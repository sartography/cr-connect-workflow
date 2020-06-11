import json
import pickle
from base64 import b64decode
from datetime import datetime

from flask import g

from crc import db, session
from crc.api.common import ApiError
from crc.models.approval import Approval, ApprovalModel, ApprovalSchema, ApprovalStatus
from crc.models.workflow import WorkflowModel
from crc.services.approval_service import ApprovalService
from crc.services.ldap_service import LdapService


# Returns counts of approvals in each status group assigned to the given user.
# The goal is to return results as quickly as possible.
def get_approval_counts(as_user=None):
    uid = as_user or g.user.uid

    db_user_approvals = db.session.query(ApprovalModel)\
        .filter_by(approver_uid=uid)\
        .filter(ApprovalModel.status != ApprovalStatus.CANCELED.name)\
        .all()

    study_ids = [a.study_id for a in db_user_approvals]

    db_other_approvals = db.session.query(ApprovalModel)\
        .filter(ApprovalModel.study_id.in_(study_ids))\
        .filter(ApprovalModel.approver_uid != uid)\
        .filter(ApprovalModel.status != ApprovalStatus.CANCELED.name)\
        .all()

    # Make a dict of the other approvals where the key is the study id and the value is the approval
    # TODO: This won't work if there are more than 2 approvals with the same study_id
    other_approvals = {}
    for approval in db_other_approvals:
        other_approvals[approval.study_id] = approval

    counts = {}
    for status in ApprovalStatus:
        counts[status.name] = 0

    for approval in db_user_approvals:
        # Check if another approval has the same study id
        if approval.study_id in other_approvals:
            other_approval = other_approvals[approval.study_id]

            # Other approval takes precedence over this one
            if other_approval.id < approval.id:
                if other_approval.status == ApprovalStatus.PENDING.name:
                    counts[ApprovalStatus.AWAITING.name] += 1
                elif other_approval.status == ApprovalStatus.DECLINED.name:
                    counts[ApprovalStatus.DECLINED.name] += 1
                elif other_approval.status == ApprovalStatus.CANCELED.name:
                    counts[ApprovalStatus.CANCELED.name] += 1
                elif other_approval.status == ApprovalStatus.APPROVED.name:
                    counts[approval.status] += 1
        else:
            counts[approval.status] += 1

    return counts


def get_all_approvals(status=None):
    approvals = ApprovalService.get_all_approvals(include_cancelled=status is True)
    results = ApprovalSchema(many=True).dump(approvals)
    return results


def get_approvals(status=None, as_user=None):
    #status = ApprovalStatus.PENDING.value
    user = g.user.uid
    if as_user:
        user = as_user
    approvals = ApprovalService.get_approvals_per_user(user, status,
                                                       include_cancelled=False)
    results = ApprovalSchema(many=True).dump(approvals)
    return results


def get_approvals_for_study(study_id=None):
    db_approvals = ApprovalService.get_approvals_for_study(study_id)
    approvals = [Approval.from_model(approval_model) for approval_model in db_approvals]
    results = ApprovalSchema(many=True).dump(approvals)
    return results


# ----- Begin descent into madness ---- #
def get_csv():
    """A damn lie, it's a json file. A huge bit of a one-off for RRT, but 3 weeks of midnight work can convince a
    man to do just about anything"""
    approvals = ApprovalService.get_all_approvals(include_cancelled=False)
    output = []
    errors = []
    for approval in approvals:
        try:
            if approval.status != ApprovalStatus.APPROVED.value:
                continue
            for related_approval in approval.related_approvals:
                if related_approval.status != ApprovalStatus.APPROVED.value:
                    continue
            workflow = db.session.query(WorkflowModel).filter(WorkflowModel.id == approval.workflow_id).first()
            data = json.loads(workflow.bpmn_workflow_json)
            last_task = find_task(data['last_task']['__uuid__'], data['task_tree'])
            personnel = extract_value(last_task, 'personnel')
            training_val = extract_value(last_task, 'RequiredTraining')
            pi_supervisor = extract_value(last_task, 'PISupervisor')['value']
            review_complete = 'AllRequiredTraining' in training_val
            pi_uid = workflow.study.primary_investigator_id
            pi_details = LdapService.user_info(pi_uid)
            details = []
            details.append(pi_details)
            for person in personnel:
                uid = person['PersonnelComputingID']['value']
                details.append(LdapService.user_info(uid))

            for person in details:
                record = {
                    "study_id": approval.study_id,
                    "pi_uid": pi_details.uid,
                    "pi": pi_details.display_name,
                    "name": person.display_name,
                    "uid": person.uid,
                    "email": person.email_address,
                    "supervisor": "",
                    "review_complete": review_complete,
                }
                # We only know the PI's supervisor.
                if person.uid == pi_details.uid:
                    record["supervisor"] = pi_supervisor

                output.append(record)

        except Exception as e:
            errors.append("Error pulling data for workflow #%i: %s" % (approval.workflow_id, str(e)))
    return {"results": output, "errors": errors }


def extract_value(task, key):
    if key in task['data']:
        return pickle.loads(b64decode(task['data'][key]['__bytes__']))
    else:
        return ""


def find_task(uuid, task):
    if task['id']['__uuid__'] == uuid:
        return task
    for child in task['children']:
        task = find_task(uuid, child)
        if task:
            return task
# ----- come back to the world of the living ---- #


def update_approval(approval_id, body):
    if approval_id is None:
        raise ApiError('unknown_approval', 'Please provide a valid Approval ID.')

    approval_model = session.query(ApprovalModel).get(approval_id)
    if approval_model is None:
        raise ApiError('unknown_approval', 'The approval "' + str(approval_id) + '" is not recognized.')

    if approval_model.approver_uid != g.user.uid:
        raise ApiError("not_your_approval", "You may not modify this approval. It belongs to another user.")

    approval_model.status = body['status']
    approval_model.message = body['message']
    approval_model.date_approved = datetime.now()
    session.add(approval_model)
    session.commit()

    # Called only to send emails
    approver = body['approver']['uid']
    ApprovalService.update_approval(approval_id, approver)

    result = ApprovalSchema().dump(approval_model)
    return result

import json
import pickle
from base64 import b64decode
from datetime import datetime

from SpiffWorkflow import Workflow
from SpiffWorkflow.serializer.dict import DictionarySerializer
from SpiffWorkflow.serializer.json import JSONSerializer
from flask import g

from crc import app, db, session

from crc.api.common import ApiError, ApiErrorSchema
from crc.models.approval import Approval, ApprovalModel, ApprovalSchema, ApprovalStatus
from crc.models.ldap import LdapSchema
from crc.models.study import Study
from crc.models.workflow import WorkflowModel
from crc.services.approval_service import ApprovalService
from crc.services.ldap_service import LdapService
from crc.services.workflow_processor import WorkflowProcessor


def get_approvals(everything=False):
    if everything:
        approvals = ApprovalService.get_all_approvals()
    else:
        approvals = ApprovalService.get_approvals_per_user(g.user.uid)
    results = ApprovalSchema(many=True).dump(approvals)
    return results


def get_approvals_for_study(study_id=None):
    db_approvals = ApprovalService.get_approvals_for_study(study_id)
    approvals = [Approval.from_model(approval_model) for approval_model in db_approvals]
    results = ApprovalSchema(many=True).dump(approvals)
    return results


# ----- Being decent into madness ---- #
def get_csv():
    """A huge bit of a one-off for RRT, but 3 weeks of midnight work can convince a
    man to do just about anything"""
    approvals = ApprovalService.get_all_approvals()
    output = []
    errors = []
    ldapService = LdapService()
    for approval in approvals:
        try:
            if approval.status != ApprovalStatus.APPROVED.value:
                continue
            for related_approval in approval.related_approvals:
                if related_approval.status != ApprovalStatus.APPROVED.value:
                    continue
            workflow = db.session.query(WorkflowModel).filter(WorkflowModel.id == approval.workflow_id).first()
            personnel = extract_personnel(workflow.bpmn_workflow_json)
            pi_uid = workflow.study.primary_investigator_id
            pi_details = ldapService.user_info(pi_uid)
            details = []
            details.append(pi_details)
            for person in personnel:
                uid = person['PersonnelComputingID']['value']
                details.append(ldapService.user_info(uid))

            for person in details:
                output.append({
                    "pi_uid": pi_details.uid,
                    "pi": pi_details.display_name,
                    "name": person.display_name,
                    "email": person.email_address
                })
        except Exception as e:
            errors.append("Error pulling data for workflow #%i: %s" % (approval.workflow_id, str(e)))
    return {"results": output, "errors": errors }

def extract_personnel(data):
    data = json.loads(data)
    last_task = find_task(data['last_task']['__uuid__'], data['task_tree'])
    last_task_personnel = pickle.loads(b64decode(last_task['data']['personnel']['__bytes__']))
    return last_task_personnel

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

    result = ApprovalSchema().dump(approval_model)
    return result

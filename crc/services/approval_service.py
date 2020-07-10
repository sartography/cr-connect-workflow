import json
import pickle
import sys
from base64 import b64decode
from datetime import datetime, timedelta

from sqlalchemy import desc, func

from crc import app, db, session
from crc.api.common import ApiError

from crc.models.approval import ApprovalModel, ApprovalStatus, ApprovalFile, Approval
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel
from crc.services.file_service import FileService
from crc.services.ldap_service import LdapService
from crc.services.mails import (
    send_ramp_up_submission_email,
    send_ramp_up_approval_request_email,
    send_ramp_up_approval_request_first_review_email,
    send_ramp_up_approved_email,
    send_ramp_up_denied_email,
    send_ramp_up_denied_email_to_approver
)

class ApprovalService(object):
    """Provides common tools for working with an Approval"""

    @staticmethod
    def __one_approval_from_study(study, approver_uid = None, status=None,
                                  include_cancelled=True):
        """Returns one approval, with all additional approvals as 'related_approvals',
        the main approval can be pinned to an approver with an optional argument.
        Will return null if no approvals exist on the study."""
        main_approval = None
        related_approvals = []
        query = db.session.query(ApprovalModel).filter(ApprovalModel.study_id == study.id)
        if not include_cancelled:
            query=query.filter(ApprovalModel.status != ApprovalStatus.CANCELED.value)
        approvals = query.all()  # All non-cancelled approvals.

        for approval_model in approvals:
            if approval_model.approver_uid == approver_uid:
                main_approval = approval_model
            else:
                related_approvals.append(approval_model)

        # IF WE ARE JUST RETURNING ALL OF THE APPROVALS PER STUDY
        if not main_approval and len(related_approvals) > 0:
            main_approval = related_approvals[0]
            related_approvals = related_approvals[1:]

        if main_approval is not None:  # May be null if the study has no approvals.
            final_status = ApprovalService.__calculate_overall_approval_status(main_approval, related_approvals)
            if status and final_status != status: return  # Now that we are certain of the status, filter on it.

            main_approval = Approval.from_model(main_approval)
            main_approval.status = final_status
            for ra in related_approvals:
                main_approval.related_approvals.append(Approval.from_model(ra))

        return main_approval

    @staticmethod
    def __calculate_overall_approval_status(approval, related):
        # In the case of pending approvals, check to see if there is a related approval
        # that proceeds this approval - and if it is declined, or still pending, then change
        # the state of the approval to be Declined, or Waiting respectively.
        if approval.status == ApprovalStatus.PENDING.value:
            for ra in related:
                if ra.id < approval.id:
                    if ra.status == ApprovalStatus.DECLINED.value or ra.status == ApprovalStatus.CANCELED.value:
                        return ra.status  # If any prior approval id declined or cancelled so is this approval.
                    elif ra.status == ApprovalStatus.PENDING.value:
                        return ApprovalStatus.AWAITING.value  # if any prior approval is pending, then this is waiting.
            return approval.status
        else:
            return approval.status

    @staticmethod
    def get_approvals_per_user(approver_uid, status=None, include_cancelled=False):
        """Returns a list of approval objects (not db models) for the given
         approver. """
        studies = db.session.query(StudyModel).join(ApprovalModel).\
            filter(ApprovalModel.approver_uid == approver_uid).all()
        approvals = []
        for study in studies:
            approval = ApprovalService.__one_approval_from_study(study, approver_uid,
                                                                 status, include_cancelled)
            if approval:
                approvals.append(approval)
        return approvals

    @staticmethod
    def get_all_approvals(include_cancelled=True):
        """Returns a list of all approval objects (not db models), one record
        per study, with any associated approvals grouped under the first approval."""
        studies = db.session.query(StudyModel).all()
        approvals = []
        for study in studies:
            approval = ApprovalService.__one_approval_from_study(study, include_cancelled=include_cancelled)
            if approval:
                approvals.append(approval)
        return approvals

    @staticmethod
    def get_approvals_for_study(study_id, include_cancelled=True):
        """Returns an array of Approval objects for the study, it does not
         compute the related approvals."""
        query = session.query(ApprovalModel).filter_by(study_id=study_id)
        if not include_cancelled:
            query = query.filter(ApprovalModel.status != ApprovalStatus.CANCELED.value)
        db_approvals = query.all()
        return [Approval.from_model(approval_model) for approval_model in db_approvals]

    @staticmethod
    def get_approval_details(approval):
        """Returns a list of packed approval details, obtained from
        the task data sent during the workflow """
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

        if approval.status != ApprovalStatus.APPROVED.value:
            return {}
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
        details = {
            'Supervisor': pi_supervisor,
            'PI_Details': pi_details,
            'Review': review_complete
        }
        details['person_details'] = []
        details['person_details'].append(pi_details)
        for person in personnel:
            uid = person['PersonnelComputingID']['value']
            details['person_details'].append(LdapService.user_info(uid))

        return details

    @staticmethod
    def get_health_attesting_records():
        """Return a list with prepared information related to all approvals """

        approvals = ApprovalService.get_all_approvals(include_cancelled=False)

        health_attesting_rows = [
            ['university_computing_id',
             'last_name',
             'first_name',
             'department',
             'job_title',
             'supervisor_university_computing_id']
        ]

        for approval in approvals:
            try:
                details = ApprovalService.get_approval_details(approval)
                if not details:
                    continue

                for person in details['person_details']:
                    first_name = person.given_name
                    last_name = person.display_name.replace(first_name, '').strip()
                    record = [
                        person.uid,
                        last_name,
                        first_name,
                        '',
                        'Academic Researcher',
                        details['Supervisor'] if person.uid == details['person_details'][0].uid else 'askresearch'
                    ]

                    if record not in health_attesting_rows:
                        health_attesting_rows.append(record)

            except Exception as e:
                app.logger.error(f'Error pulling data for workflow {approval.workflow_id}', exc_info=True)

        return health_attesting_rows

    @staticmethod
    def get_not_really_csv_content():
        approvals = ApprovalService.get_all_approvals(include_cancelled=False)
        output = []
        errors = []
        for approval in approvals:
            try:
                details = ApprovalService.get_approval_details(approval)

                for person in details['person_details']:
                    record = {
                        "study_id": approval.study_id,
                        "pi_uid": details['PI_Details'].uid,
                        "pi": details['PI_Details'].display_name,
                        "name": person.display_name,
                        "uid": person.uid,
                        "email": person.email_address,
                        "supervisor": details['Supervisor'] if person.uid == details['person_details'][0].uid else "",
                        "review_complete": details['Review'],
                    }

                    output.append(record)

            except Exception as e:
                errors.append(
                    f'Error pulling data for workflow #{approval.workflow_id} '
                    f'(Approval status: {approval.status} - '
                    f'More details in Sentry): {str(e)}'
                )
                # Detailed information sent to Sentry
                app.logger.error(f'Error pulling data for workflow {approval.workflow_id}', exc_info=True)
        return {"results": output, "errors": errors }

    @staticmethod
    def update_approval(approval_id, approver_uid):
        """Update a specific approval
        NOTE: Actual update happens in the API layer, this
        funtion is currently in charge of only sending
        corresponding emails
        """
        db_approval = session.query(ApprovalModel).get(approval_id)
        status = db_approval.status
        if db_approval:
            if status == ApprovalStatus.APPROVED.value:
                # second_approval = ApprovalModel().query.filter_by(
                #     study_id=db_approval.study_id, workflow_id=db_approval.workflow_id,
                #     status=ApprovalStatus.PENDING.value, version=db_approval.version).first()
                # if second_approval:
                    # send rrp approval request for second approver
                ldap_service = LdapService()
                pi_user_info = ldap_service.user_info(db_approval.study.primary_investigator_id)
                approver_info = ldap_service.user_info(approver_uid)
                # send rrp submission
                mail_result = send_ramp_up_approved_email(
                    'askresearch@virginia.edu',
                    [pi_user_info.email_address],
                    f'{approver_info.display_name} - ({approver_info.uid})'
                )
                if mail_result:
                    app.logger.error(mail_result, exc_info=True)
            elif status == ApprovalStatus.DECLINED.value:
                ldap_service = LdapService()
                pi_user_info = ldap_service.user_info(db_approval.study.primary_investigator_id)
                approver_info = ldap_service.user_info(approver_uid)
                # send rrp submission
                mail_result = send_ramp_up_denied_email(
                    'askresearch@virginia.edu',
                    [pi_user_info.email_address],
                    f'{approver_info.display_name} - ({approver_info.uid})'
                )
                if mail_result:
                    app.logger.error(mail_result, exc_info=True)
                first_approval = ApprovalModel().query.filter_by(
                    study_id=db_approval.study_id, workflow_id=db_approval.workflow_id,
                    status=ApprovalStatus.APPROVED.value, version=db_approval.version).first()
                if first_approval:
                    # Second approver denies
                    first_approver_info = ldap_service.user_info(first_approval.approver_uid)
                    approver_email = [first_approver_info.email_address] if first_approver_info.email_address else app.config['FALLBACK_EMAILS']
                    # send rrp denied by second approver email to first approver
                    mail_result = send_ramp_up_denied_email_to_approver(
                        'askresearch@virginia.edu',
                        approver_email,
                        f'{pi_user_info.display_name} - ({pi_user_info.uid})',
                        f'{approver_info.display_name} - ({approver_info.uid})'
                    )
                    if mail_result:
                        app.logger.error(mail_result, exc_info=True)

        return db_approval

    @staticmethod
    def add_approval(study_id, workflow_id, approver_uid):
        """we might have multiple approvals for a workflow, so I would expect this
            method to get called multiple times for the same workflow.  This will
            only add a new approval if no approval already exists for the approver_uid,
            unless the workflow has changed, at which point, it will CANCEL any
            pending approvals and create a new approval for the latest version
            of the workflow."""

        # Find any existing approvals for this workflow.
        latest_approval_requests = db.session.query(ApprovalModel). \
            filter(ApprovalModel.workflow_id == workflow_id). \
            order_by(desc(ApprovalModel.version))

        latest_approver_request = latest_approval_requests.filter(ApprovalModel.approver_uid == approver_uid).first()

        # Construct as hash of the latest files to see if things have changed since
        # the last approval.
        workflow = db.session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        workflow_data_files = FileService.get_workflow_data_files(workflow_id)
        current_data_file_ids = list(data_file.id for data_file in workflow_data_files)

        if len(current_data_file_ids) == 0:
            raise ApiError("invalid_workflow_approval", "You can't create an approval for a workflow that has"
                                                        "no files to approve in it.")

        # If an existing approval request exists and no changes were made, do nothing.
        # If there is an existing approval request for a previous version of the workflow
        # then add a new request, and cancel any waiting/pending requests.
        if latest_approver_request:
            request_file_ids = list(file.file_data_id for file in latest_approver_request.approval_files)
            current_data_file_ids.sort()
            request_file_ids.sort()
            other_approver = latest_approval_requests.filter(ApprovalModel.approver_uid != approver_uid).first()
            if current_data_file_ids == request_file_ids:
                return  # This approval already exists or we're updating other approver.
            else:
                for approval_request in latest_approval_requests:
                    if (approval_request.version == latest_approver_request.version and
                        approval_request.status != ApprovalStatus.CANCELED.value):
                        approval_request.status = ApprovalStatus.CANCELED.value
                        db.session.add(approval_request)
                version = latest_approver_request.version + 1
        else:
            version = 1

        model = ApprovalModel(study_id=study_id, workflow_id=workflow_id,
                              approver_uid=approver_uid, status=ApprovalStatus.PENDING.value,
                              message="", date_created=datetime.now(),
                              version=version)
        approval_files = ApprovalService._create_approval_files(workflow_data_files, model)

        # Check approvals count
        approvals_count = ApprovalModel().query.filter_by(study_id=study_id, workflow_id=workflow_id,
                                        version=version).count()

        db.session.add(model)
        db.session.add_all(approval_files)
        db.session.commit()

        # Send first email
        if approvals_count == 0:
            ldap_service = LdapService()
            pi_user_info = ldap_service.user_info(model.study.primary_investigator_id)
            approver_info = ldap_service.user_info(approver_uid)
            # send rrp submission
            mail_result = send_ramp_up_submission_email(
                'askresearch@virginia.edu',
                [pi_user_info.email_address],
                f'{approver_info.display_name} - ({approver_info.uid})'
            )
            if mail_result:
                app.logger.error(mail_result, exc_info=True)
            # send rrp approval request for first approver
            # enhance the second part in case it bombs
            approver_email = [approver_info.email_address] if approver_info.email_address else app.config['FALLBACK_EMAILS']
            mail_result = send_ramp_up_approval_request_first_review_email(
                'askresearch@virginia.edu',
                approver_email,
                f'{pi_user_info.display_name} - ({pi_user_info.uid})'
            )
            if mail_result:
                app.logger.error(mail_result, exc_info=True)

    @staticmethod
    def _create_approval_files(workflow_data_files, approval):
        """Currently based exclusively on the status of files associated with a workflow."""
        file_approval_models = []
        for file_data in workflow_data_files:
            file_approval_models.append(ApprovalFile(file_data_id=file_data.id,
                                                     approval=approval))
        return file_approval_models


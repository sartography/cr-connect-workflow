from crc import session
from crc.api.common import ApiError
from crc.models.study import StudyModel
from crc.models.task_event import TaskEventModel
from crc.services.ldap_service import LdapService
from crc.services.study_service import StudyService
from crc.scripts.script import Script
from crc.models.workflow import WorkflowModel


class GetWaitingBCA(Script):

    @staticmethod
    def get_study_url(study_id):
        return StudyService.get_study_url(study_id)

    def get_description(self):
        return """Return a list of all BCA workflows that are waiting for approval."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    @staticmethod
    def __get_study_title(study_id):
        """Return the study title for the given study ID."""
        study = session.query(StudyModel).filter(StudyModel.id == study_id).first()
        if study:
            return study.title
        else:
            raise ApiError("study_not_found", "Study not found", status_code=404)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        """Return a list of all BCA workflows that are waiting for approval."""
        waiting_bca = []
        task_event_results = (session.query(TaskEventModel).
                              filter(TaskEventModel.action=='ASSIGNMENT').
                              filter(TaskEventModel.workflow_spec_id=='billing_coverage_analysis').
                              filter(TaskEventModel.task_title=='Approval Request').
                              all())
        if task_event_results:
            # format the output
            for task_event in task_event_results:
                # if task_event.task_lane == 'PIApprover':
                user_info = None
                if LdapService.user_exists(task_event.user_uid):
                    user_info = LdapService.user_info(task_event.user_uid)
                output = {'study_id': task_event.study_id,
                          'user_uid': task_event.user_uid,
                          'user_name': user_info.display_name if user_info else task_event.user_uid,
                          'workflow_id': task_event.workflow_id,
                          'date': task_event.date,
                          'study_url': self.get_study_url(task_event.study_id),
                          'study_title': self.__get_study_title(task_event.study_id)}
                waiting_bca.append(output)

        return waiting_bca


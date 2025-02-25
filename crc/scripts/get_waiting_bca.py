from crc.api.common import ApiError
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

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        """Return a list of all BCA workflows that are waiting for approval."""
        waiting_bca = []
        query_results = (WorkflowModel.query.
                       filter(WorkflowModel.workflow_spec_id=='billing_coverage_analysis').
                       filter(WorkflowModel.status=='waiting').
                       all())
        if query_results:
            # format the output
            for workflow in query_results:
                output = {}
                output['study_id'] = workflow.study_id
                output['study_short_title'] = workflow.study.short_title
                output['study_title'] = workflow.study.title
                output['study_url'] = self.get_study_url(workflow.study_id)
                waiting_bca.append(output)
            print('here')
        return waiting_bca


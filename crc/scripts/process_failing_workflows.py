from crc import app, session
from crc.api.workflow import restart_workflow
from crc.scripts.script import Script
from crc.services.workflow_service import WorkflowService
from crc.models.workflow import WorkflowModel, WorkflowStatus


class ProcessFailingWorkflows(Script):

    def get_description(self):
        return """This is an admin script to restart failing workflows."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    @staticmethod
    def _get_workflow_url(workflow_id):
        """Get workflow URL, allow non-secure connections in development."""
        workflow_url = WorkflowService().get_workflow_url(workflow_id)
        if ('DEVELOPMENT' in app.config and
                app.config['DEVELOPMENT'] is True and workflow_url.startswith('https://')):
            workflow_url = workflow_url.replace('https://', 'http://')
        # else:
        #     workflow_url = "https://"
        # workflow_url += f"{app.config['SERVER_NAME']}/v1.0/workflow/{workflow_id}/restart"
        return workflow_url

    def _process_failing_workflows(self, failing_workflows):
        failing_workflow_ids = []
        failing_workflow_url_links = []
        for failing_workflow in failing_workflows:
            failing_workflow_ids.append(failing_workflow.id)
            failing_workflow_url_link = self._get_workflow_url(failing_workflow.id)
            failing_workflow_url_links.append(failing_workflow_url_link)
        return failing_workflow_ids, failing_workflow_url_links

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        """Return a list of failing workflows. Restart the workflows if requested."""
        mode = kwargs.get('mode', None)
        if mode is not None:
            failing_workflows = (
                session.query(WorkflowModel).
                filter(WorkflowModel.status == WorkflowStatus.erroring).
                all()
            )
            failing_workflow_ids, failing_workflow_url_links = (
                self._process_failing_workflows(failing_workflows))

            if mode == 'get':
                return failing_workflow_url_links

            if mode == 'restart':
                restart_errors = []
                for failing_workflow_id in failing_workflow_ids:
                    try:
                        restart_workflow(failing_workflow_id, clear_data=False)
                    except Exception as e:
                        error_message = f"Failed to restart workflow {failing_workflow_id}: {e}"
                        print(error_message)
                        restart_errors.append(error_message)
                    finally:
                        print(f"Restarted workflow {failing_workflow_id}")
                remaining_failing_workflows = (
                    session.query(WorkflowModel).
                    filter(WorkflowModel.status == WorkflowStatus.erroring).
                    all()
                )
                return restart_errors, remaining_failing_workflows

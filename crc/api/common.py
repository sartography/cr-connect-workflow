from SpiffWorkflow import WorkflowException
from SpiffWorkflow.exceptions import WorkflowTaskExecException
from flask import g

from crc import ma, app

import sentry_sdk


class ApiError(Exception):
    def __init__(self, code, message, status_code=400,
                 file_name="", task_id="", task_name="", tag="", task_data = {}):
        self.status_code = status_code
        self.code = code  # a short consistent string describing the error.
        self.message = message  # A detailed message that provides more information.
        self.task_id = task_id or ""  # OPTIONAL:  The id of the task in the BPMN Diagram.
        self.task_name = task_name or ""  # OPTIONAL: The name of the task in the BPMN Diagram.
        self.file_name = file_name or ""  # OPTIONAL: The file that caused the error.
        self.tag = tag or ""  # OPTIONAL: The XML Tag that caused the issue.
        self.task_data = task_data or ""  # OPTIONAL: A snapshot of data connected to the task when error ocurred.
        if hasattr(g,'user'):
            user = g.user.uid
        else:
            user = 'Unknown'
        self.task_user = user
        # This is for sentry logging into Slack
        sentry_sdk.set_context("User", {'user': user})
        Exception.__init__(self, self.message)

    @classmethod
    def from_task(cls, code, message, task, status_code=400):
        """Constructs an API Error with details pulled from the current task."""
        instance = cls(code, message, status_code=status_code)
        instance.task_id = task.task_spec.name or ""
        instance.task_name = task.task_spec.description or ""
        instance.file_name = task.workflow.spec.file or ""

        # Fixme: spiffworkflow is doing something weird where task ends up referenced in the data in some cases.
        if "task" in task.data:
            task.data.pop("task")

        instance.task_data = task.data
        app.logger.error(message, exc_info=True)
        return instance

    @classmethod
    def from_task_spec(cls, code, message, task_spec, status_code=400):
        """Constructs an API Error with details pulled from the current task."""
        instance = cls(code, message, status_code=status_code)
        instance.task_id = task_spec.name or ""
        instance.task_name = task_spec.description or ""
        if task_spec._wf_spec:
            instance.file_name = task_spec._wf_spec.file
        app.logger.error(message, exc_info=True)
        return instance

    @classmethod
    def from_workflow_exception(cls, code, message, exp: WorkflowException):
        """We catch a lot of workflow exception errors,
            so consolidating the code, and doing the best things
            we can with the data we have."""
        if isinstance(exp, WorkflowTaskExecException):
            return ApiError.from_task(code, message, exp.task)
        else:
            return ApiError.from_task_spec(code, message, exp.sender)


class ApiErrorSchema(ma.Schema):
    class Meta:
        fields = ("code", "message", "workflow_name", "file_name", "task_name", "task_id",
                  "task_data", "task_user", "hint")


@app.errorhandler(ApiError)
def handle_invalid_usage(error):
    response = ApiErrorSchema().dump(error)
    return response, error.status_code



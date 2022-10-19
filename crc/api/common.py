import json

from flask import g
from jinja2 import TemplateError
from werkzeug.exceptions import InternalServerError
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.bpmn.exceptions import WorkflowTaskExecException

from crc import ma, app

import sentry_sdk


class ApiError(Exception):
    def __init__(self, code, message, status_code=400,
                 file_name="", task_id="", task_name="", tag="",
                 task_data=None, error_type="", error_line="", line_number=0, offset=0,
                 task_trace=None):
        if task_data is None:
            task_data = {}
        if task_trace is None:
            task_trace = {}
        self.status_code = status_code
        self.code = code  # a short consistent string describing the error.
        self.message = message  # A detailed message that provides more information.
        self.task_id = task_id or ""  # OPTIONAL:  The id of the task in the BPMN Diagram.
        self.task_name = task_name or ""  # OPTIONAL: The name of the task in the BPMN Diagram.
        self.file_name = file_name or ""  # OPTIONAL: The file that caused the error.
        self.tag = tag or ""  # OPTIONAL: The XML Tag that caused the issue.
        self.task_data = task_data or ""  # OPTIONAL: A snapshot of data connected to the task when error occurred.
        self.line_number = line_number
        self.offset = offset
        self.error_type = error_type
        self.error_line = error_line
        self.task_trace = task_trace

        try:
            user = g.user.uid
        except Exception as e:
            user = 'Unknown'
        self.task_user = user
        # This is for sentry logging into Slack
        sentry_sdk.set_context("User", {'user': user})
        Exception.__init__(self, self.message)

    def __str__(self):
        msg = "ApiError: % s. " % self.message
        if self.task_name:
            msg += "Error in task '%s' (%s). " % (self.task_name, self.task_id)
        if self.line_number:
            msg += "Error is on line %i. " % self.line_number
        if self.file_name:
            msg += "In file %s. " % self.file_name
        return msg

    @classmethod
    def from_task(cls, code, message, task, status_code=400, line_number=0, offset=0, error_type="", error_line="",
                  task_trace=None):
        """Constructs an API Error with details pulled from the current task."""
        instance = cls(code, message, status_code=status_code)
        instance.task_id = task.task_spec.name or ""
        instance.task_name = task.task_spec.description or ""
        instance.file_name = task.workflow.spec.file or ""
        instance.line_number = line_number
        instance.offset = offset
        instance.error_type = error_type
        instance.error_line = error_line
        if task_trace:
            instance.task_trace = task_trace
        else:
            instance.task_trace = WorkflowTaskExecException.get_task_trace(task)

        # Fixme: spiffworkflow is doing something weird where task ends up referenced in the data in some cases.
        if "task" in task.data:
            task.data.pop("task")

        # Assure that there is nothing in the json data that can't be serialized.
        instance.task_data = ApiError.remove_unserializeable_from_dict(task.data)

        app.logger.error(message, exc_info=True)
        return instance

    @staticmethod
    def remove_unserializeable_from_dict(my_dict):
        keys_to_delete = []
        for key, value in my_dict.items():
            if not ApiError.is_jsonable(value):
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del my_dict[key]
        return my_dict

    @staticmethod
    def is_jsonable(x):
        try:
            json.dumps(x)
            return True
        except (TypeError, OverflowError, ValueError):
            return False

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
            return ApiError.from_task(code, message, exp.task, line_number=exp.line_number,
                                      offset=exp.offset,
                                      error_type=exp.exception.__class__.__name__,
                                      error_line=exp.error_line,
                                      task_trace=exp.task_trace)

        else:
            return ApiError.from_task_spec(code, message, exp.sender)


class ApiErrorSchema(ma.Schema):
    class Meta:
        fields = ("code", "message", "workflow_name", "file_name", "task_name", "task_id",
                  "task_data", "task_user", "hint", "line_number", "offset", "error_type",
                  "error_line", "task_trace")


@app.errorhandler(ApiError)
def handle_invalid_usage(error):
    response = ApiErrorSchema().dump(error)
    return response, error.status_code


@app.errorhandler(InternalServerError)
def handle_internal_server_error(e):
    original = getattr(e, "original_exception", None)
    api_error = ApiError(code='Internal Server Error (500)', message=str(original))
    response = ApiErrorSchema().dump(api_error)
    return response, 500

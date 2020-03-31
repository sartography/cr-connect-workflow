from crc import ma, app


class ApiError(Exception):
    def __init__(self, code, message, status_code=400,
                 file_name="", task_id="", task_name="", tag=""):
        self.status_code = status_code
        self.code = code  # a short consistent string describing the error.
        self.message = message  # A detailed message that provides more information.
        self.task_id = task_id or ""  # OPTIONAL:  The id of the task in the BPMN Diagram.
        self.task_name = task_name or ""  # OPTIONAL: The name of the task in the BPMN Diagram.
        self.file_name = file_name or ""  # OPTIONAL: The file that caused the error.
        self.tag = tag or ""  # OPTIONAL: The XML Tag that caused the issue.
        Exception.__init__(self, self.message)

    @classmethod
    def from_task(cls, code, message, task, status_code=400):
        """Constructs an API Error with details pulled from the current task."""
        instance = cls(code, message, status_code=status_code)
        instance.task_id = task.task_spec.name or ""
        instance.task_name = task.task_spec.description or ""
        instance.file_name = task.workflow.spec.file or ""
        return instance

    @classmethod
    def from_task_spec(cls, code, message, task_spec, status_code=400):
        """Constructs an API Error with details pulled from the current task."""
        instance = cls(code, message, status_code=status_code)
        instance.task_id = task_spec.name or ""
        instance.task_name = task_spec.description or ""
        if task_spec._wf_spec:
            instance.file_name = task_spec._wf_spec.file
        return instance


class ApiErrorSchema(ma.Schema):
    class Meta:
        fields = ("code", "message", "workflow_name", "file_name", "task_name", "task_id")


@app.errorhandler(ApiError)
def handle_invalid_usage(error):
    response = ApiErrorSchema().dump(error)
    return response, error.status_code

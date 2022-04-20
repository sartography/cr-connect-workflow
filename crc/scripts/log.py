from SpiffWorkflow.exceptions import WorkflowTaskExecException

from crc.models.task_log import TaskLogModel, TaskLogModelSchema, TaskLogLevels
from crc.scripts.script import Script
from crc.services.task_logging_service import TaskLoggingService


class TaskLog(Script):

    def get_description(self):
        return """Script to log events in a Script Task.
        Takes `level`, `code`, and `message` arguments.
        Example:
            log(level='info', code='missing_info', message='You must include the correct info!')
        
        Level must be `debug`, `info`, `warning`, `error`, `critical`, `metrics`
        Code is a short string meant for searching the logs. By convention, it is lower case with underscores.
        Message is a more descriptive string, including any info you want to log.
        """

    def get_arguments(self, task, *args, **kwargs):
        # Returns a level, code, and message from the given arguments, or raises an error.
        if len(args) == 3 or ('level' in kwargs and 'code' in kwargs and 'message' in kwargs):
            if 'level' in kwargs:
                level = kwargs['level']
            else:
                level = args[0]
            if 'code' in kwargs:
                code = kwargs['code']
            else:
                code = args[1]
            if 'message' in kwargs:
                message = kwargs['message']
            else:
                message = args[2]

            if level not in TaskLogLevels:
                raise WorkflowTaskExecException(task, f'You must supply a valid log level, one of ({TaskLogLevels})'
                                                      f' when calling the log() script.  You specified "{level}"')

            return level, code, message
        else:
            raise WorkflowTaskExecException(task, 'You must include a level, code, and message'
                                                  ' when calling the log() script')

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        level, code, message = self.get_arguments(task, *args, **kwargs)
        log_model = TaskLogModel(level=level,
                                 code=code,
                                 message=message,
                                 study_id=study_id,
                                 workflow_id=workflow_id,
                                 task=task.get_name())
        return TaskLogModelSchema().dump(log_model)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        level, code, message = self.get_arguments(task, *args, **kwargs)
        log_model = TaskLoggingService.add_log(task, level, code, message, study_id, workflow_id)
        return TaskLogModelSchema().dump(log_model)

from crc import session
from crc.models.task_log import TaskLogModel, TaskLogModelSchema, TaskLogQuery
from crc.scripts.script import Script
from crc.services.task_logging_service import TaskLoggingService


class GetLogsByWorkflow(Script):

    def get_description(self):
        return """Script to retrieve logs for the current study. 
        Accepts an optional `code` argument that is used to filter the DB query.
        Accepts an optional 'size' otherwise will return the most recent 10 records.
        """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        log_model = TaskLogModel(level='metrics',
                                 code='mocked_code',
                                 message='This is my logging message',
                                 study_id=study_id,
                                 workflow_id=workflow_id,
                                 task=task.get_name())
        return TaskLogModelSchema(many=True).dump([log_model])

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        level = None
        code = None
        size = None
        if 'level' in kwargs:
            level = kwargs['level']
        elif len(args) > 0:
            level = args[0]
        if 'code' in kwargs:
            code = kwargs['code']
        elif len(args) > 1:
            code = args[1]
        if 'size' in kwargs:
            size = kwargs['size']
        elif len(args) > 2:
            size = args[2]

        log_models = TaskLoggingService().get_logs_for_study(study_id, level, code, size)
        return TaskLogModelSchema(many=True).dump(log_models)

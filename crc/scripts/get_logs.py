from crc import session
from crc.api.common import ApiError
from crc.models.task_log import TaskLogModel, TaskLogModelSchema
from crc.scripts.script import Script


class GetLogsByWorkflow(Script):

    def get_description(self):
        return """Script to retrieve logs for the current workflow. 
        Accepts an optional `code` argument that is used to filter the DB query.
        """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        log_model = TaskLogModel(level='info',
                                 code='mocked_code',
                                 message='This is my logging message',
                                 study_id=study_id,
                                 workflow_id=workflow_id,
                                 task=task.get_name())
        TaskLogModelSchema(many=True).dump([log_model])

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        code = None
        if 'code' in kwargs:
            code = kwargs['code']
        elif len(args) > 0:
            code = args[0]
        if code is not None:
            log_models = session.query(TaskLogModel).\
                filter(TaskLogModel.code == code).\
                filter(TaskLogModel.workflow_id == workflow_id).\
                all()
        else:
            log_models = session.query(TaskLogModel). \
                filter(TaskLogModel.workflow_id == workflow_id). \
                all()

        return TaskLogModelSchema(many=True).dump(log_models)

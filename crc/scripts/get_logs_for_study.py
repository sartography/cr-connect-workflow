from crc import session
from crc.api.common import ApiError
from crc.models.task_log import TaskLogModel, TaskLogModelSchema
from crc.scripts.script import Script


class GetLogsByWorkflow(Script):

    def get_description(self):
        return """Script to retrieve logs for the current study. 
        Accepts an optional `code` argument that is used to filter the DB query.
        """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) == 1 or 'code' in kwargs:
            pass
        else:
            raise ApiError.from_task(code='missing_code',
                                     message='You must include a `code` to use in the search.',
                                     task=task)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        code = None
        if 'code' in kwargs:
            code = kwargs['code']
        elif len(args) > 0:
            code = args[0]
        if code is not None:
            log_models = session.query(TaskLogModel).\
                filter(TaskLogModel.code == code).\
                filter(TaskLogModel.study_id == study_id).\
                all()
        else:
            log_models = session.query(TaskLogModel). \
                filter(TaskLogModel.study_id == study_id). \
                all()

        return TaskLogModelSchema(many=True).dump(log_models)

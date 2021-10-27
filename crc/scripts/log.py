from crc import session
from crc.api.common import ApiError
from crc.models.task_log import TaskLogModel, TaskLogModelSchema
from crc.scripts.script import Script


class MyScript(Script):

    def get_description(self):
        return """Script to log events in a Script Task.
        Takes `level`, `code`, and `message` arguments.
        Example:
            log(level='info', code='missing_info', message='You must include the correct info!')
        
        Level must be `debug`, `info`, `warning`, `error` or `critical`.
        Code is a short string meant for searching the logs.
        Message is a more descriptive string, including any info you want to log.
        """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        pass

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) == 3 or ('level' in kwargs and 'code' in kwargs and 'message' in kwargs):
            if 'level' in kwargs:
                level = kwargs['level']
            else:
                level = args[0]
            if 'code' in kwargs:
                code = kwargs['code']
            else:
                code = args[0]
            if 'message' in kwargs:
                message = kwargs['message']
            else:
                message = args[0]
            task_name = task.get_name()
            log_model = TaskLogModel(level=level,
                                     code=code,
                                     message=message,
                                     study_id=study_id,
                                     workflow_id=workflow_id,
                                     task=task_name)
            session.add(log_model)
            session.commit()

            print('do_task')
            return TaskLogModelSchema().dump(log_model)

        else:
            raise ApiError.from_task(code='missing_arguments',
                                     message='You must include a level, code, and message to log.',
                                     task=task)

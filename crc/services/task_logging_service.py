from crc import app, session
from crc.api.common import ApiError
from crc.models.task_log import TaskLogModel, TaskLogLevels, TaskLogQuery, TaskLogModelSchema
from crc.models.workflow import WorkflowModel
from crc.services.user_service import UserService

from sqlalchemy import desc

import dateparser
import pytz


class TaskLoggingService(object):
    """Provides common tools for logging information from running workflows.  This logging information
       Can be useful in metrics, and as a means of showing what is happening over time.  For this reason
       we will record some of this data in the database, at least for now.  We will also add this information
       to our standard logs so all the details exist somewhere, even if the information in the database
       is truncated or modified. """

    @staticmethod
    def add_log(task, level, code, message, study_id, workflow_id):
        if level not in TaskLogLevels:
            raise ApiError("invalid_logging_level", f"Please specify a valid log level. {TaskLogLevels}")
        try:
            user_uid = UserService.current_user().uid
        except ApiError as e:
            user_uid = "unknown"
        if workflow_id:
            workflow_spec_id = session.query(WorkflowModel.workflow_spec_id).\
                filter(WorkflowModel.id == workflow_id).\
                scalar()
        else:
            workflow_spec_id = None
        log_message = f"Workflow Spec {workflow_spec_id}, study {study_id}, task {task.get_name()}, user {user_uid}: {message}"
        app.logger.log(TaskLogLevels[level].value, log_message)
        log_model = TaskLogModel(level=level,
                                 code=code,
                                 message=message,
                                 study_id=study_id,
                                 workflow_id=workflow_id,
                                 task=task.get_name(),
                                 user_uid=user_uid,
                                 workflow_spec_id=workflow_spec_id)
        session.add(log_model)
        session.commit()
        return log_model

    def get_logs_for_workflow(self, workflow_id: int, level: str = None, code: str = None, size: int = None):
        logs = self.get_logs(workflow_id=workflow_id, level=level, code=code, size=size)
        return logs

    def get_logs_for_study(self, study_id: int, level: str = None, code: str = None, size: int = None):
        logs = self.get_logs(study_id=study_id, level=level, code=code, size=size)
        return logs

    @staticmethod
    def get_logs(study_id: int = None, workflow_id: int = None, level: str = None, code: str = None, size: int = None):
        """We should almost always get a study_id or a workflow_id.
           In *very* rare circumstances, an admin may want all the logs.
           This could be a *lot* of logs."""
        query = session.query(TaskLogModel)
        if study_id:
            query = query.filter(TaskLogModel.study_id == study_id)
        if workflow_id:
            query = query.filter(TaskLogModel.workflow_id == workflow_id)
        if level:
            query = query.filter(TaskLogModel.level == level)
        if code:
            query = query.filter(TaskLogModel.code == code)
        if size:
            query = query.limit(size)
        logs = query.all()
        return logs

    @staticmethod
    def get_logs_for_study_paginated(study_id, tq: TaskLogQuery):
        """ Returns an updated TaskLogQuery, with items in reverse chronological order by default. """
        query = session.query(TaskLogModel).filter(TaskLogModel.study_id == study_id)
        return TaskLoggingService.__paginate(query, tq)

    @staticmethod
    def __paginate(sql_query, task_log_query: TaskLogQuery):
        """Updates the given sql_query with parameters from the task log query, executes it, then updates the
         task_log_query with the results from the SQL Query"""
        if not task_log_query:
            task_log_query = TaskLogQuery()
        if task_log_query.sort_column is None:
            task_log_query.sort_column = "timestamp"
            task_log_query.sort_reverse = True
        if task_log_query.code:
            sql_query = sql_query.filter(TaskLogModel.code.like(task_log_query.code + "%"))
        if task_log_query.level:
            sql_query = sql_query.filter(TaskLogModel.level.like(task_log_query.level + "%"))
        if task_log_query.user:
            sql_query = sql_query.filter(TaskLogModel.user_uid.like(task_log_query.user + "%"))
        if task_log_query.sort_reverse:
            sort_column = desc(task_log_query.sort_column)
        else:
            sort_column = task_log_query.sort_column
        paginator = sql_query.order_by(sort_column).paginate(task_log_query.page + 1, task_log_query.per_page,
                                                             error_out=False)
        task_log_query.update_from_sqlalchemy_paginator(paginator)
        return task_log_query

    @staticmethod
    def get_log_data_for_download(study_id):
        # Admins can download the metrics logs for a study as an Excel file
        # We only use a subset of the fields
        logs = []
        headers = []
        result = session.query(TaskLogModel).\
            filter(TaskLogModel.study_id == study_id).\
            filter(TaskLogModel.level == 'metrics').\
            all()
        schemas = TaskLogModelSchema(many=True).dump(result)
        # We only use these fields
        fields = ['category', 'workflow', 'level', 'code', 'message', 'user_uid', 'timestamp', 'workflow_id', 'workflow_spec_id']
        for schema in schemas:
            # Build a dictionary using the items in fields
            log = {}
            for field in fields:
                if field == 'timestamp':
                    # Excel doesn't accept timezones,
                    # so we return a local datetime without the timezone
                    # TODO: detect the local timezone with something like dateutil.tz.tzlocal()
                    parsed_timestamp = dateparser.parse(str(schema['timestamp']))
                    localtime = parsed_timestamp.astimezone(pytz.timezone('US/Eastern'))
                    log[field] = localtime.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    log[field] = schema[field]
                if field.capitalize() not in headers:
                    headers.append(field.capitalize())
            logs.append(log)

        return logs, headers

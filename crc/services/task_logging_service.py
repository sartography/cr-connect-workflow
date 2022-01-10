import markdown
import re

from flask import render_template
from flask_mail import Message
from jinja2 import Template
from sqlalchemy import desc

from crc import app, db, mail, session
from crc.api.common import ApiError

from crc.models.email import EmailModel
from crc.models.file import FileDataModel
from crc.models.study import StudyModel
from crc.models.task_log import TaskLogModel, TaskLogLevels, TaskLogQuery
from crc.models.user import UserModel

from crc.services.jinja_service import JinjaService
from crc.services.user_service import UserService


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
        log_message = f"Workflow {workflow_id}, study {study_id}, task {task.get_name()}, user {user_uid}: {message}"
        app.logger.log(TaskLogLevels[level].value, log_message)
        log_model = TaskLogModel(level=level,
                                 code=code,
                                 user_uid=user_uid,
                                 message=message,
                                 study_id=study_id,
                                 workflow_id=workflow_id,
                                 task=task.get_name())
        session.add(log_model)
        session.commit()
        return log_model

    @staticmethod
    def get_logs_for_workflow(workflow_id, tq: TaskLogQuery):
        """ Returns an updated TaskLogQuery, with items in reverse chronological order by default. """
        query = session.query(TaskLogModel).filter(TaskLogModel.workflow_id == workflow_id)
        return TaskLoggingService.__paginate(query, tq)

    @staticmethod
    def get_logs_for_study(study_id, tq: TaskLogQuery):
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
        if task_log_query.code is not None:
            sql_query = sql_query.filter(TaskLogModel.code == task_log_query.code)
        if task_log_query.sort_reverse:
            sort_column = desc(task_log_query.sort_column)
        else:
            sort_column = task_log_query.sort_column
        paginator = sql_query.order_by(sort_column).paginate(task_log_query.page, task_log_query.per_page,
                                                             error_out=False)
        task_log_query.update_from_sqlalchemy_paginator(paginator)
        return task_log_query

import enum
import urllib

import flask
import marshmallow
from flask import url_for
from marshmallow.fields import Method

from crc import db, ma
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel
from crc.services.workflow_spec_service import WorkflowSpecService
from sqlalchemy import func


class MyEnumMeta(enum.EnumMeta):
    def __contains__(cls, item):
        return item in [v.name for v in cls.__members__.values()]


class TaskLogLevels(enum.Enum, metaclass=MyEnumMeta):
    critical = 50
    error = 40
    warning = 30
    info = 20
    debug = 10
    metrics = 5


class TaskLogModel(db.Model):
    __tablename__ = 'task_log'
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String)
    code = db.Column(db.String)
    message = db.Column(db.String)
    user_uid = db.Column(db.String)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=False)
    workflow_id = db.Column(db.Integer, db.ForeignKey(WorkflowModel.id), nullable=False)
    workflow_spec_id = db.Column(db.String)
    task = db.Column(db.String)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())


class TaskLogModelSchema(ma.Schema):
    class Meta:
        model = TaskLogModel
        fields = ["id", "level", "code", "message", "study_id", "workflow", "workflow_id",
                  "workflow_spec_id", "category", "user_uid", "timestamp"]
    category = marshmallow.fields.Method('get_category')
    workflow = marshmallow.fields.Method('get_workflow')

    @staticmethod
    def get_category(obj):
        if hasattr(obj, 'workflow_spec_id') and obj.workflow_spec_id is not None:
            workflow_spec = WorkflowSpecService().get_spec(obj.workflow_spec_id)
            if workflow_spec:
                category = WorkflowSpecService().get_category(workflow_spec.category_id)
                if category:
                    return category.display_name

    @staticmethod
    def get_workflow(obj):
        if hasattr(obj, 'workflow_spec_id') and obj.workflow_spec_id is not None:
            workflow_spec = WorkflowSpecService().get_spec(obj.workflow_spec_id)
            if workflow_spec:
                return workflow_spec.display_name


class TaskLogQuery:
    """Encapsulates the paginated queries and results when retrieving and filtering task logs over the
    API"""
    def __init__(self, study_id=None, code="", level="", user="", page=0, per_page=10,
                 sort_column=None, sort_reverse=False, items=None,
                 pages=0, total=0, has_next=False, has_prev=False, download_url=None):
        self.study_id = study_id  # Filter on Study.
        self.code = code  # Filter on code.
        self.level = level  # Filter on level.
        self.user = user  # Filter on user.
        self.page = page
        self.per_page = per_page
        self.sort_column = sort_column
        self.sort_reverse = sort_reverse
        self.items = items
        self.total = total
        self.pages = pages
        self.has_next = False
        self.has_prev = False
        self.download_url = None

    def update_from_sqlalchemy_paginator(self, paginator):
        """Updates this with results that are returned from the paginator"""
        self.items = paginator.items
        self.page = paginator.page - 1
        self.per_page = paginator.per_page
        self.pages = paginator.pages
        self.has_next = paginator.has_next
        self.has_prev = paginator.has_prev
        self.total = paginator.total


class TaskLogQuerySchema(ma.Schema):
    class Meta:
        model = TaskLogModel
        fields = ["code", "level", "user",
                  "page", "per_page", "sort_column", "sort_reverse", "items", "pages", "total",
                  "has_next", "has_prev", "download_url"]
    items = marshmallow.fields.List(marshmallow.fields.Nested(TaskLogModelSchema))
    download_url = Method("get_url")

    def get_url(self, obj):
        token = 'not_available'
        if hasattr(obj, 'study_id') and obj.study_id is not None:
            file_url = url_for("/v1_0.crc_api_study_download_logs_for_study", study_id=obj.study_id, _external=True)
            if hasattr(flask.g, 'user'):
                token = flask.g.user.encode_auth_token()
            url = file_url + '?auth_token=' + urllib.parse.quote_plus(token)
            return url
        else:
            return ""


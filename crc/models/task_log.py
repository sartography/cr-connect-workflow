import enum

import marshmallow

from crc import db, ma
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel
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
    task = db.Column(db.String)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())


class TaskLogModelSchema(ma.Schema):
    class Meta:
        model = TaskLogModel
        fields = ["id", "level", "code", "message", "study_id", "workflow_id", "user_uid", "timestamp"]


class TaskLogQuery:
    """Encapsulates the paginated queries and results when retrieving and filtering task logs over the
    API"""
    def __init__(self, code="", level="", user="", page=1, per_page=10,
                 sort_column=None, sort_reverse=False, items=None,
                 pages=0, total=0, has_next=False, has_prev=False):
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

    def update_from_sqlalchemy_paginator(self, paginator):
        """Updates this with results that are returned from the paginator"""
        self.items = paginator.items
        self.page = paginator.page
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
                  "has_next", "has_prev"]
    items = marshmallow.fields.List(marshmallow.fields.Nested(TaskLogModelSchema))
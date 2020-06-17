# Admin app
import json

from flask import url_for
from flask_admin import Admin
from flask_admin.contrib import sqla
from flask_admin.contrib.sqla import ModelView
from werkzeug.utils import redirect
from jinja2 import Markup

from crc import db, app
from crc.api.user import verify_token, verify_token_admin
from crc.models.approval import ApprovalModel
from crc.models.file import FileModel
from crc.models.stats import TaskEventModel
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowModel


class AdminModelView(sqla.ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50  # the number of entries to display on the list view
    column_exclude_list = ['bpmn_workflow_json', ]
    column_display_pk = True
    can_export = True

    def is_accessible(self):
        return verify_token_admin()

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('home'))

class UserView(AdminModelView):
    column_filters = ['uid']

class StudyView(AdminModelView):
    column_filters = ['id', 'primary_investigator_id']
    column_searchable_list = ['title']

class ApprovalView(AdminModelView):
    column_filters = ['study_id', 'approver_uid']

class WorkflowView(AdminModelView):
    column_filters = ['study_id', 'id']

class FileView(AdminModelView):
    column_filters = ['workflow_id']

def json_formatter(view, context, model, name):
    value = getattr(model, name)
    json_value = json.dumps(value, ensure_ascii=False, indent=2)
    return Markup('<pre>{}</pre>'.format(json_value))

class TaskEventView(AdminModelView):
    column_filters = ['workflow_id', 'action']
    column_list = ['study_id', 'user_id', 'workflow_id', 'action', 'task_title', 'task_data', 'date']
    column_formatters = {
        'task_data': json_formatter,
    }

admin = Admin(app)

admin.add_view(StudyView(StudyModel, db.session))
admin.add_view(ApprovalView(ApprovalModel, db.session))
admin.add_view(UserView(UserModel, db.session))
admin.add_view(WorkflowView(WorkflowModel, db.session))
admin.add_view(FileView(FileModel, db.session))
admin.add_view(TaskEventView(TaskEventModel, db.session))

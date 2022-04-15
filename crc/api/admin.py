# Admin app
import json

from flask import url_for
from flask_admin import Admin
from flask_admin.actions import action
from flask_admin.contrib import sqla
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import desc
from werkzeug.utils import redirect
from jinja2.utils import markupsafe
from crc import db, app
from crc.api.common import ApiError
from crc.api.user import verify_token, verify_token_admin
from crc.models.file import FileModel, FileDataModel
from crc.models.task_event import TaskEventModel
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
    column_filters = ['id']
    column_searchable_list = ['title']


class ApprovalView(AdminModelView):
    column_filters = ['study_id', 'approver_uid']


class WorkflowView(AdminModelView):
    column_filters = ['study_id', 'id']


class FileView(AdminModelView):
    column_filters = ['workflow_id', 'type']

    @action('publish', 'Publish', 'Are you sure you want to publish this file(s)?')
    def action_publish(self, ids):
        raise ApiError("not_implemented", "This method is not yet implemented.")

    @action('update', 'Update', 'Are you sure you want to update this file(s)?')
    def action_update(self, ids):
        raise ApiError("not_implemented", "This method is not yet implemented.")


def json_formatter(view, context, model, name):
    value = getattr(model, name)
    json_value = json.dumps(value, ensure_ascii=False, indent=2)
    return markupsafe.Markup(f'<pre>{json_value}</pre>')

class TaskEventView(AdminModelView):
    column_filters = ['workflow_id', 'action']
    column_list = ['study_id', 'user_id', 'workflow_id', 'action', 'task_title', 'form_data', 'date']
    column_formatters = {
        'form_data': json_formatter,
    }


admin = Admin(app)

admin.add_view(StudyView(StudyModel, db.session))
admin.add_view(UserView(UserModel, db.session))
admin.add_view(WorkflowView(WorkflowModel, db.session))
admin.add_view(FileView(FileModel, db.session))
admin.add_view(TaskEventView(TaskEventModel, db.session))

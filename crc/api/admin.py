# Admin app
import json

from flask import url_for
from flask_admin import Admin
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from werkzeug.utils import redirect
from jinja2.utils import markupsafe
from crc import db, app
from crc.api.common import ApiError
from crc.api.user import verify_token, verify_token_admin
from crc.models.data_store import DataStoreModel
from crc.models.email import EmailModel
from crc.models.file import FileModel
from crc.models.task_event import TaskEventModel
from crc.models.study import StudyModel
from crc.models.task_log import TaskLogModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowModel


class AdminModelView(ModelView):
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
    can_create = True
    can_edit = True
    can_delete = True


class ApprovalView(AdminModelView):
    column_filters = ['study_id', 'approver_uid']


class WorkflowView(AdminModelView):
    column_filters = ['study_id', 'id']


class FileView(AdminModelView):
    column_filters = ['workflow_id', 'type']
    column_exclude_list = ['data']
    can_create = True
    can_edit = True
    can_delete = True

    @action('publish', 'Publish', 'Are you sure you want to publish this file(s)?')
    def action_publish(self, ids):
        raise ApiError("not_implemented", "This method is not yet implemented.")

    @action('update', 'Update', 'Are you sure you want to update this file(s)?')
    def action_update(self, ids):
        raise ApiError("not_implemented", "This method is not yet implemented.")


class EmailView(AdminModelView):
    column_exclude_list = ['id', 'content_html']
    column_searchable_list = ['name', 'subject']
    column_filters = ['subject', 'name', 'study_id']
    can_create = True
    can_edit = True
    can_delete = True


class TaskLogView(AdminModelView):
    column_exclude_list = ['id']
    column_searchable_list = ['code', 'message', 'task']
    column_filters = ['level', 'code', 'study_id', 'workflow_id', 'workflow_spec_id']
    can_create = True
    can_edit = True
    can_delete = True


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


class DataStoreView(AdminModelView):
    column_filters = ['key', 'study_id', 'user_id', 'file_id']
    column_list = ['key', 'value', 'study_id', 'user_id', 'file_id', 'workflow_id']


admin = Admin(app)

admin.add_view(StudyView(StudyModel, db.session))
admin.add_view(UserView(UserModel, db.session))
admin.add_view(WorkflowView(WorkflowModel, db.session))
admin.add_view(FileView(FileModel, db.session))
admin.add_view(TaskEventView(TaskEventModel, db.session))
admin.add_view(EmailView(EmailModel, db.session))
admin.add_view(TaskLogView(TaskLogModel, db.session))
admin.add_view(DataStoreView(DataStoreModel, db.session))

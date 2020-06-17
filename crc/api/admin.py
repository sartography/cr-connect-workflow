# Admin app

from flask import url_for
from flask_admin import Admin
from flask_admin.contrib import sqla
from flask_admin.contrib.sqla import ModelView
from werkzeug.utils import redirect

from crc import db, app
from crc.api.user import verify_token, verify_token_admin
from crc.models.approval import ApprovalModel
from crc.models.file import FileModel
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

admin = Admin(app)

admin.add_view(StudyView(StudyModel, db.session))
admin.add_view(ApprovalView(ApprovalModel, db.session))
admin.add_view(UserView(UserModel, db.session))
admin.add_view(WorkflowView(WorkflowModel, db.session))
admin.add_view(FileView(FileModel, db.session))

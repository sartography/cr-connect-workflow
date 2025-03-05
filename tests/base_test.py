# Set environment variable to testing before loading.
# IMPORTANT - Environment must be loaded before app, models, etc....
import os


os.environ["TESTING"] = "true"

import json
import unittest
import urllib.parse
import datetime
import shutil
from flask import g

from crc import app, db, session
from crc.models.api_models import WorkflowApiSchema, MultiInstanceType
from crc.models.task_event import TaskEventModel, TaskAction
from crc.models.study import StudyModel, StudyStatus, ProgressStatus
from crc.models.user import UserModel
from crc.models.workflow import WorkflowSpecCategory
from crc.services.ldap_service import LdapService
from crc.services.reference_file_service import ReferenceFileService
from crc.services.spec_file_service import SpecFileService
from crc.services.study_service import StudyService
from crc.services.user_service import UserService
from crc.services.document_service import DocumentService
from example_data import ExampleDataLoader
from crc.services.workflow_spec_service import WorkflowSpecService
from crc.services.workflow_service import WorkflowService
from crc.services.workflow_processor import WorkflowProcessor

# UNCOMMENT THIS FOR DEBUGGING SQL ALCHEMY QUERIES
import logging

logging.basicConfig()


class BaseTest(unittest.TestCase):
    """ Great class to inherit from, as it sets up and tears down classes
        efficiently when we have a database in place.
    """
    workflow_spec_service = WorkflowSpecService()

    if not app.config['TESTING']:
        raise (Exception("INVALID TEST CONFIGURATION. This is almost always in import order issue."
                         "The first class to import in each test should be the base_test.py file."))

    auths = {}
    test_uid = "dhf8r"

    # These users correspond to the ldap details available in our mock ldap service.
    users = [
        {
            'uid': 'dhf8r',
        },
        {
            'uid': 'lb3dp',
        },
        {
            'uid': 'kcm4zc',
        }
    ]

    studies = [
        {
            'id': 0,
            'title': 'The impact of fried pickles on beer consumption in bipedal software developers.',
            'last_updated': datetime.datetime.utcnow(),
            'status': StudyStatus.in_progress,
            'progress_status': ProgressStatus.in_progress,
            'sponsor': 'Sartography Pharmaceuticals',
            'ind_number': '1234',
            'user_uid': 'dhf8r',
            'review_type': 2
        },
        {
            'id': 1,
            'title': 'Requirement of hippocampal neurogenesis for the behavioral effects of soft pretzels',
            'last_updated': datetime.datetime.utcnow(),
            'status': StudyStatus.in_progress,
            'progress_status': ProgressStatus.in_progress,
            'sponsor': 'Makerspace & Co.',
            'ind_number': '5678',
            'user_uid': 'dhf8r',
            'review_type': 2
        }
    ]

    @classmethod
    def setUpClass(cls):
        cls.clear_test_sync_files()
        app.config.from_object('config.testing')
        cls.ctx = app.test_request_context()
        cls.app = app.test_client()
        cls.ctx.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.commit()
        db.drop_all()
        cls.ctx.pop()

    def setUp(self):
        self.clear_test_sync_files()

    def tearDown(self):
        ExampleDataLoader.clean_db()
        self.logout()
        self.auths = {}
        self.clear_test_sync_files()

    @staticmethod
    def copy_files_to_file_system(import_spec_path, spec_path):
        """Some tests rely on a well populated file system """
        shutil.copytree(import_spec_path, spec_path)

    @staticmethod
    def clear_test_sync_files():
        sync_file_root = SpecFileService().root_path()
        if os.path.exists(sync_file_root):
            shutil.rmtree(sync_file_root)

    def logged_in_headers(self, user=None, redirect_url='http://some/frontend/url'):
        if user is None:
            uid = self.test_uid
            user_info = {'uid': self.test_uid}
        else:
            uid = user.uid
            user_info = {'uid': user.uid}

        query_string = self.user_info_to_query_string(user_info, redirect_url)
        rv = self.app.get("/v1.0/login%s" % query_string, follow_redirects=False)
        self.assertTrue(rv.status_code == 302)
        self.assertTrue(str.startswith(rv.location, redirect_url))

        user_model = session.query(UserModel).filter_by(uid=uid).first()
        self.assertIsNotNone(user_model.ldap_info.display_name)
        self.assertEqual(user_model.uid, uid)
        self.assertTrue('user' in g, 'User should be in Flask globals')
        user = UserService.current_user(allow_admin_impersonate=True)
        self.assertEqual(uid, user.uid, 'Logged in user should match given user uid')

        return dict(Authorization='Bearer ' + user_model.encode_auth_token())

    def delete_example_data(self, use_crc_data=False, use_rrt_data=False):
        """
        delete everything that matters in the local database - this is used to
        test ground zero copy of workflow specs.
        """
        ExampleDataLoader.clean_db()

    @staticmethod
    def add_user(ldap_model):
        db.session.add(ldap_model)
        db.session.commit()
        db.session.add(UserModel(uid=ldap_model.uid, ldap_info=ldap_model))


    def add_users(self):
        added_user = False
        for user_json in self.users:
            ldap_info = LdapService.user_info(user_json['uid'])
            already_user = session.query(UserModel).filter_by(uid=user_json['uid']).first()
            if not already_user:
                added_user = True
                session.add(UserModel(uid=user_json['uid'], ldap_info=ldap_info))
        if added_user:
            session.commit()

    def add_studies(self):
        self.add_users()
        for study_json in self.studies:
            study_model = StudyModel(**study_json)
            session.add(study_model)
            update_seq = f"ALTER SEQUENCE %s RESTART WITH %s" % (StudyModel.__tablename__ + '_id_seq', study_model.id + 1)
            session.execute(update_seq)
        session.commit()


    def assure_category_name_exists(self, name):
        category = self.workflow_spec_service.get_category(name)
        if category is None:
            category = WorkflowSpecCategory(id=name, display_name=name, admin=False, display_order=0)
            self.workflow_spec_service.add_category(category)
        return category

    def assure_category_exists(self, category_id=None, display_name="Test Workflows", admin=False):
        category = None
        if category_id is not None:
            category = self.workflow_spec_service.get_category(category_id)
        if category is None:
            if category_id is None:
                category_id = 'test_category'
            category = WorkflowSpecCategory(id=category_id, display_name=display_name, admin=admin, display_order=0)
            self.workflow_spec_service.add_category(category)
        return category

    def load_test_spec(self, dir_name, display_name=None, master_spec=False, category_id=None, library=False):
        """Loads a spec into the database based on a directory in /tests/data"""
        category = None
        if not master_spec and not library:
            category = self.assure_category_exists(category_id)
            category_id = category.id
        workflow_spec = self.workflow_spec_service.get_spec(dir_name)
        if workflow_spec:
            return workflow_spec
        else:
            filepath = os.path.join(app.root_path, '..', 'tests', 'data', dir_name, "*")
            if display_name is None:
                display_name = dir_name
            spec = ExampleDataLoader().create_spec(id=dir_name, filepath=filepath, master_spec=master_spec,
                                                   display_name=display_name, category_id=category_id, library=library)
            return spec

    @staticmethod
    def protocol_builder_response(file_name):
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', 'pb_responses', file_name)
        with open(filepath, 'r') as myfile:
            data = myfile.read()
        return data

    @staticmethod
    def workflow_sync_response(file_name):
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', 'workflow_sync_responses', file_name)
        with open(filepath, 'rb') as myfile:
            data = myfile.read()
        return data

    def assert_success(self, rv, msg=""):
        error_message = ""
        try:
            data = json.loads(rv.get_data(as_text=True))
            if 'message' in data:
                error_message = data['message']
        except Exception as e:
            # Can't get an error message from the body.
            error_message = "unparsable response"

        self.assertTrue(200 <= rv.status_code < 300,
                        "BAD Response: %i. \n %s" %
                        (rv.status_code, error_message + ". " + msg + ". "))

    def assert_failure(self, rv, status_code=0, error_code=""):
        self.assertFalse(200 <= rv.status_code < 300,
                         "Incorrect Valid Response:" + rv.status + ".")
        if status_code != 0:
            self.assertEqual(status_code, rv.status_code)
        if error_code != "":
            data = json.loads(rv.get_data(as_text=True))
            self.assertEqual(error_code, data["code"])

    def assert_dict_contains_subset(self, container, subset):
        def extract_dict_a_from_b(a, b):
            return dict([(k, b[k]) for k in a.keys() if k in b.keys()])

        extract = extract_dict_a_from_b(subset, container)
        self.assertEqual(subset, extract)

    @staticmethod
    def user_info_to_query_string(user_info, redirect_url):
        query_string_list = []
        items = user_info.items()
        for key, value in items:
            query_string_list.append('%s=%s' % (key, urllib.parse.quote(value)))

        query_string_list.append('redirect_url=%s' % redirect_url)

        return '?%s' % '&'.join(query_string_list)

    def replace_file(self, spec, name, file_path):
        """Replaces a stored file with the given name with the contents of the file at the given path."""
        file = open(file_path, "rb")
        data = file.read()
        SpecFileService().update_file_data(spec, name, data)

    def create_user(self, uid="dhf8r", email="daniel.h.funk@gmail.com", display_name="Hoopy Frood"):
        user = session.query(UserModel).filter(UserModel.uid == uid).first()
        if user is None:
            ldap_user = LdapService.user_info(uid)
            user = UserModel(uid=uid, ldap_info=ldap_user)
            session.add(user)
            session.commit()
        return user

    def create_study(self, uid="dhf8r", title="Beer consumption in the bipedal software engineer"):
        study = session.query(StudyModel).filter_by(user_uid=uid).filter_by(title=title).first()
        if study is None:
            user = self.create_user(uid=uid)
            study = StudyModel(title=title, status=StudyStatus.in_progress,
                               user_uid=user.uid, review_type=2)
            session.add(study)
            session.commit()
        return study

    def create_workflow(self, dir_name, display_name=None, study=None, category_id=None, as_user="dhf8r"):
        session.flush()
        spec = self.workflow_spec_service.get_spec(dir_name)
        if spec is None:
            if display_name is None:
                display_name = dir_name
            spec = self.load_test_spec(dir_name, display_name, category_id=category_id)
        if study is None:
            study = self.create_study(uid=as_user)
        workflow_model = StudyService._create_workflow_model(study, spec)
        return workflow_model

    def create_reference_document(self):
        file_path = os.path.join(app.root_path, 'static', 'reference', 'documents.xlsx')
        with open(file_path, "rb") as file:
            ReferenceFileService.add_reference_file(DocumentService.DOCUMENT_LIST,
                                                    file.read())
        file_path = os.path.join(app.root_path, 'static', 'reference', 'investigators.xlsx')
        with open(file_path, "rb") as file:
            ReferenceFileService.add_reference_file('investigators.xlsx',
                                                    file.read())

    def get_workflow_common(self, url, user):
        rv = self.app.get(url,
                          headers=self.logged_in_headers(user),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        json_data['user_id'] = user.uid
        workflow_api = WorkflowApiSchema().load(json_data)
        return workflow_api

    def get_workflow_api(self, workflow, do_engine_steps=True, user_uid="dhf8r"):
        user = session.query(UserModel).filter_by(uid=user_uid).first()
        self.assertIsNotNone(user)
        url = (f'/v1.0/workflow/{workflow.id}'
               f'?do_engine_steps={str(do_engine_steps)}')
        workflow_api = self.get_workflow_common(url, user)
        self.assertEqual(workflow.workflow_spec_id, workflow_api.workflow_spec_id)
        return workflow_api

    def restart_workflow_api(self, workflow, clear_data=False, delete_files=False, user_uid="dhf8r"):
        user = session.query(UserModel).filter_by(uid=user_uid).first()
        self.assertIsNotNone(user)
        url = (f'/v1.0/workflow/{workflow.id}/restart'
               f'?clear_data={str(clear_data)}'
               f'&delete_files={str(delete_files)}')
        workflow_api = self.get_workflow_common(url, user)
        self.assertEqual(workflow.workflow_spec_id, workflow_api.workflow_spec_id)
        return workflow_api

    def complete_form(self, workflow_in, task_in, dict_data, update_all=False, error_code=None, terminate_loop=None,
                      user_uid="dhf8r"):
        # workflow_in should be a workflow, not a workflow_api
        # we were passing in workflow_api in many of our tests, and
        # this caused problems testing standalone workflows
        spec = self.workflow_spec_service.get_spec(workflow_in.workflow_spec_id)
        standalone = getattr(spec, 'standalone', False)
        prev_completed_task_count = workflow_in.completed_tasks
        if isinstance(task_in, dict):
            task_id = task_in["id"]
        else:
            task_id = task_in.id

        user = session.query(UserModel).filter_by(uid=user_uid).first()
        self.assertIsNotNone(user)
        args = ""
        if terminate_loop:
            args += "?terminate_loop=true"
        if update_all:
            args += "?update_all=true"

        rv = self.app.put('/v1.0/workflow/%i/task/%s/data%s' % (workflow_in.id, task_id, args),
                          headers=self.logged_in_headers(user=user),
                          content_type="application/json",
                          data=json.dumps(dict_data))
        if error_code:
            self.assert_failure(rv, error_code=error_code)
            return

        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))

        # Assure task events are updated on the model
        json_data['user_id'] = user_uid
        workflow = WorkflowApiSchema().load(json_data)

        # Assure a record exists in the Task Events
        task_events = session.query(TaskEventModel) \
            .filter_by(workflow_id=workflow.id) \
            .filter_by(task_id=task_id) \
            .filter_by(action=TaskAction.COMPLETE.value) \
            .order_by(TaskEventModel.date.desc()).all()
        self.assertGreater(len(task_events), 0)
        event = task_events[0]
        if not standalone:
            self.assertIsNotNone(event.study_id)
        self.assertEqual(user_uid, event.user_uid)
        self.assertEqual(workflow.id, event.workflow_id)
        self.assertEqual(workflow.workflow_spec_id, event.workflow_spec_id)
        self.assertEqual(TaskAction.COMPLETE.value, event.action)
        self.assertEqual(task_in.id, task_id)
        self.assertEqual(task_in.name, event.task_name)
#        self.assertEqual(task_in.title, event.task_title)   // Completed events may get the wrong title.
        self.assertEqual(task_in.type, event.task_type)
        if not task_in.multi_instance_type == 'looping':
            self.assertEqual("COMPLETED", event.task_state)

        # Not sure what voodoo is happening inside of marshmallow to get me in this state.
        if isinstance(task_in.multi_instance_type, MultiInstanceType):
            self.assertEqual(task_in.multi_instance_type.value, event.mi_type)
        else:
            self.assertEqual(task_in.multi_instance_type, event.mi_type)

        self.assertEqual(task_in.multi_instance_count, event.mi_count)
        if task_in.multi_instance_type == 'looping' and not terminate_loop:
            self.assertEqual(task_in.multi_instance_index + 1, event.mi_index)
        else:
            self.assertEqual(task_in.multi_instance_index, event.mi_index)
        self.assertEqual(task_in.process_name, event.process_name)
        self.assertIsNotNone(event.date)

        workflow = WorkflowApiSchema().load(json_data)
        return workflow

    def logout(self):
        if 'user' in g:
            del g.user

        if 'impersonate_user' in g:
            del g.impersonate_user

    @staticmethod
    def minimal_bpmn(content):
        """Returns a bytesIO object of a well formed BPMN xml file with some string content of your choosing."""
        minimal_dbpm = "<x><process id='1' isExecutable='false'><startEvent id='a'/></process>%s</x>"
        return (minimal_dbpm % content).encode()

    @staticmethod
    def run_master_spec(study_model):
        spec_service = WorkflowSpecService()
        master_spec = spec_service.master_spec
        master_workflow_results = WorkflowProcessor.run_master_spec(master_spec, study_model)
        WorkflowService().update_workflow_state_from_master_workflow(study_model.id, master_workflow_results)

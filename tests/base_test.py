# Set environment variable to testing before loading.
# IMPORTANT - Environment must be loaded before app, models, etc....
import os

os.environ["TESTING"] = "true"

import json
import unittest
import urllib.parse
import datetime
from flask import g
from sqlalchemy import Sequence

from crc import app, db, session
from crc.models.api_models import WorkflowApiSchema, MultiInstanceType
from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES
from crc.models.task_event import TaskEventModel
from crc.models.study import StudyModel, StudyStatus
from crc.models.data_store import DataStoreModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecCategoryModel
from crc.services.file_service import FileService
from crc.services.study_service import StudyService
from crc.services.user_service import UserService
from crc.services.workflow_service import WorkflowService
from example_data import ExampleDataLoader

# UNCOMMENT THIS FOR DEBUGGING SQL ALCHEMY QUERIES
import logging

logging.basicConfig()


class BaseTest(unittest.TestCase):
    """ Great class to inherit from, as it sets up and tears down classes
        efficiently when we have a database in place.
    """

    if not app.config['TESTING']:
        raise (Exception("INVALID TEST CONFIGURATION. This is almost always in import order issue."
                         "The first class to import in each test should be the base_test.py file."))

    auths = {}
    test_uid = "dhf8r"

    users = [
        {
            'uid': 'dhf8r',
            'email_address': 'dhf8r@virginia.EDU',
            'display_name': 'Daniel Harold Funk',
            'affiliation': 'staff@virginia.edu;member@virginia.edu',
            'eppn': 'dhf8r@virginia.edu',
            'first_name': 'Daniel',
            'last_name': 'Funk',
            'title': 'SOFTWARE ENGINEER V'
        },
        {
            'uid': 'lbd3p',
            'email_address': 'lbd3p@virginia.EDU',
            'display_name': 'Laura Barnes',
            'affiliation': 'staff@virginia.edu;member@virginia.edu',
            'eppn': 'lbd3p@virginia.edu',
            'first_name': 'Laura',
            'last_name': 'Barnes',
            'title': 'Associate Professor of Systems and Information Engineering'
        },
    ]

    studies = [
        {
            'id': 0,
            'title': 'The impact of fried pickles on beer consumption in bipedal software developers.',
            'last_updated': datetime.datetime.utcnow(),
            'status': StudyStatus.in_progress,
            'primary_investigator_id': 'dhf8r',
            'sponsor': 'Sartography Pharmaceuticals',
            'ind_number': '1234',
            'user_uid': 'dhf8r'
        },
        {
            'id': 1,
            'title': 'Requirement of hippocampal neurogenesis for the behavioral effects of soft pretzels',
            'last_updated': datetime.datetime.utcnow(),
            'status': StudyStatus.in_progress,
            'primary_investigator_id': 'dhf8r',
            'sponsor': 'Makerspace & Co.',
            'ind_number': '5678',
            'user_uid': 'dhf8r'
        }
    ]

    @classmethod
    def setUpClass(cls):
        app.config.from_object('config.testing')
        cls.ctx = app.test_request_context()
        cls.app = app.test_client()
        cls.ctx.push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()
        db.drop_all()
        pass

    def setUp(self):
        pass

    def tearDown(self):
        ExampleDataLoader.clean_db()
        self.logout()
        self.auths = {}

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
        self.assertIsNotNone(user_model.display_name)
        self.assertEqual(user_model.uid, uid)
        self.assertTrue('user' in g, 'User should be in Flask globals')
        user = UserService.current_user(allow_admin_impersonate=True)
        self.assertEqual(uid, user.uid, 'Logged in user should match given user uid')

        return dict(Authorization='Bearer ' + user_model.encode_auth_token().decode())

    def delete_example_data(self, use_crc_data=False, use_rrt_data=False):
        """
        delete everything that matters in the local database - this is used to
        test ground zero copy of workflow specs.
        """
        session.execute("delete from workflow; delete from file_data; delete from file; delete from workflow_spec;")
        session.commit()

    def load_example_data(self, use_crc_data=False, use_rrt_data=False):
        """use_crc_data will cause this to load the mammoth collection of documents
        we built up developing crc, use_rrt_data will do the same for hte rrt project,
         otherwise it depends on a small setup for running tests."""
        from example_data import ExampleDataLoader
        ExampleDataLoader.clean_db()
        if use_crc_data:
            ExampleDataLoader().load_all()
        elif use_rrt_data:
            ExampleDataLoader().load_rrt()
        else:
            ExampleDataLoader().load_test_data()

        # If in production mode, only add the first user.
        if app.config['PRODUCTION']:
            session.add(UserModel(**self.users[0]))
        else:
            for user_json in self.users:
                session.add(UserModel(**user_json))

        session.commit()
        for study_json in self.studies:
            study_model = StudyModel(**study_json)
            session.add(study_model)
            StudyService._add_all_workflow_specs_to_study(study_model)
            session.commit()
            update_seq = f"ALTER SEQUENCE %s RESTART WITH %s" % (StudyModel.__tablename__ + '_id_seq', study_model.id + 1)
            print("Update Sequence." + update_seq)
            session.execute(update_seq)
        session.flush()

        specs = session.query(WorkflowSpecModel).all()
        self.assertIsNotNone(specs)

        for spec in specs:
            files = session.query(FileModel).filter_by(workflow_spec_id=spec.id).all()
            self.assertIsNotNone(files)
            self.assertGreater(len(files), 0)
            for file in files:
                file_data = session.query(FileDataModel).filter_by(file_model_id=file.id).all()
                self.assertIsNotNone(file_data)
                self.assertGreater(len(file_data), 0)

    @staticmethod
    def load_test_spec(dir_name, display_name=None, master_spec=False, category_id=None):
        """Loads a spec into the database based on a directory in /tests/data"""
        if category_id is None:
            category = WorkflowSpecCategoryModel(name="test", display_name="Test Workflows", display_order=0)
            session.add(category)
            session.commit()
            category_id = category.id

        if session.query(WorkflowSpecModel).filter_by(id=dir_name).count() > 0:
            return session.query(WorkflowSpecModel).filter_by(id=dir_name).first()
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', dir_name, "*")
        if display_name is None:
            display_name = dir_name
        return ExampleDataLoader().create_spec(id=dir_name, name=dir_name, filepath=filepath, master_spec=master_spec,
                                               display_name=display_name, category_id=category_id)

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
        try:
            data = json.loads(rv.get_data(as_text=True))
            self.assertTrue(200 <= rv.status_code < 300,
                            "BAD Response: %i. \n %s" %
                            (rv.status_code, json.dumps(data)) + ". " + msg)
        except:
            self.assertTrue(200 <= rv.status_code < 300,
                            "BAD Response: %i." % rv.status_code + ". " + msg)

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

    def replace_file(self, name, file_path):
        """Replaces a stored file with the given name with the contents of the file at the given path."""
        file_service = FileService()
        file = open(file_path, "rb")
        data = file.read()

        file_model = session.query(FileModel).filter(FileModel.name == name).first()
        noise, file_extension = os.path.splitext(file_path)
        content_type = CONTENT_TYPES[file_extension[1:]]
        file_service.update_file(file_model, data, content_type)

    def create_user(self, uid="dhf8r", email="daniel.h.funk@gmail.com", display_name="Hoopy Frood"):
        user = session.query(UserModel).filter(UserModel.uid == uid).first()
        if user is None:
            user = UserModel(uid=uid, email_address=email, display_name=display_name)
            session.add(user)
            session.commit()
        return user

    def create_study(self, uid="dhf8r", title="Beer consumption in the bipedal software engineer",
                     primary_investigator_id="lb3dp"):
        study = session.query(StudyModel).filter_by(user_uid=uid).filter_by(title=title).first()
        if study is None:
            user = self.create_user(uid=uid)
            study = StudyModel(title=title, status=StudyStatus.in_progress,
                               user_uid=user.uid, primary_investigator_id=primary_investigator_id)
            session.add(study)
            session.commit()
        return study

    def _create_study_workflow_approvals(self, user_uid, title, primary_investigator_id, approver_uids, statuses,
                                         workflow_spec_name="random_fact"):
        study = self.create_study(uid=user_uid, title=title, primary_investigator_id=primary_investigator_id)
        workflow = self.create_workflow(workflow_name=workflow_spec_name, study=study)
        approvals = []

        for i in range(len(approver_uids)):
            approvals.append(self.create_approval(
                study=study,
                workflow=workflow,
                approver_uid=approver_uids[i],
                status=statuses[i],
                version=1
            ))

        full_study = {
            'study': study,
            'workflow': workflow,
            'approvals': approvals,
        }

        return full_study

    def create_workflow(self, workflow_name, display_name=None, study=None, category_id=None, as_user="dhf8r"):
        session.flush()
        spec = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.name == workflow_name).first()
        if spec is None:
            if display_name is None:
                display_name = workflow_name
            spec = self.load_test_spec(workflow_name, display_name, category_id=category_id)
        if study is None:
            study = self.create_study(uid=as_user)
        workflow_model = StudyService._create_workflow_model(study, spec)
        return workflow_model

    def create_reference_document(self):
        file_path = os.path.join(app.root_path, 'static', 'reference', 'irb_documents.xlsx')
        file = open(file_path, "rb")
        FileService.add_reference_file(FileService.DOCUMENT_LIST,
                                       binary_data=file.read(),
                                       content_type=CONTENT_TYPES['xls'])
        file.close()

    def create_approval(
            self,
            study=None,
            workflow=None,
            approver_uid=None,
            status=None,
            version=None,
    ):
        study = study or self.create_study()
        workflow = workflow or self.create_workflow()
        approver_uid = approver_uid or self.test_uid
        status = status or ApprovalStatus.PENDING.value
        version = version or 1
        approval = ApprovalModel(study=study, workflow=workflow, approver_uid=approver_uid, status=status,
                                 version=version)
        session.add(approval)
        session.commit()
        return approval

    def get_workflow_common(self, url, user):
        rv = self.app.get(url,
                          headers=self.logged_in_headers(user),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
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
        standalone = getattr(workflow_in.workflow_spec, 'standalone', False)
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
        workflow = WorkflowApiSchema().load(json_data)
        # The total number of tasks may change over time, as users move through gateways
        # branches may be pruned. As we hit parallel Multi-Instance new tasks may be created...
        self.assertIsNotNone(workflow.total_tasks)
        # presumably, we also need to deal with sequential items here too . .
        if not task_in.multi_instance_type == 'looping' and not update_all:
            self.assertEqual(prev_completed_task_count + 1, workflow.completed_tasks)

        # Assure a record exists in the Task Events
        task_events = session.query(TaskEventModel) \
            .filter_by(workflow_id=workflow.id) \
            .filter_by(task_id=task_id) \
            .filter_by(action=WorkflowService.TASK_ACTION_COMPLETE) \
            .order_by(TaskEventModel.date.desc()).all()
        self.assertGreater(len(task_events), 0)
        event = task_events[0]
        if not standalone:
            self.assertIsNotNone(event.study_id)
        self.assertEqual(user_uid, event.user_uid)
        self.assertEqual(workflow.id, event.workflow_id)
        self.assertEqual(workflow.workflow_spec_id, event.workflow_spec_id)
        self.assertEqual(workflow.spec_version, event.spec_version)
        self.assertEqual(WorkflowService.TASK_ACTION_COMPLETE, event.action)
        self.assertEqual(task_in.id, task_id)
        self.assertEqual(task_in.name, event.task_name)
        self.assertEqual(task_in.title, event.task_title)
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

    def minimal_bpmn(self, content):
        """Returns a bytesIO object of a well formed BPMN xml file with some string content of your choosing."""
        minimal_dbpm = "<x><process id='1' isExecutable='false'><startEvent id='a'/></process>%s</x>"
        return (minimal_dbpm % content).encode()


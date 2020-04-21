# Set environment variable to testing before loading.
# IMPORTANT - Environment must be loaded before app, models, etc....
import json
import os
import unittest
import urllib.parse
import datetime

from crc.models.protocol_builder import ProtocolBuilderStatus
from crc.models.study import StudyModel
from crc.services.file_service import FileService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor

os.environ["TESTING"] = "true"

from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel
from crc.models.user import UserModel

from crc import app, db, session
from example_data import ExampleDataLoader

# UNCOMMENT THIS FOR DEBUGGING SQL ALCHEMY QUERIES
# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


class BaseTest(unittest.TestCase):
    """ Great class to inherit from, as it sets up and tears down classes
        efficiently when we have a database in place.
    """

    auths = {}
    test_uid = "dhf8r"

    users = [
        {
            'uid':'dhf8r',
            'email_address':'dhf8r@virginia.EDU',
            'display_name':'Daniel Harold Funk',
            'affiliation':'staff@virginia.edu;member@virginia.edu',
            'eppn':'dhf8r@virginia.edu',
            'first_name':'Daniel',
            'last_name':'Funk',
            'title':'SOFTWARE ENGINEER V'
        }
    ]

    studies = [
        {
            'id':0,
            'title':'The impact of fried pickles on beer consumption in bipedal software developers.',
            'last_updated':datetime.datetime.now(),
            'protocol_builder_status':ProtocolBuilderStatus.ACTIVE,
            'primary_investigator_id':'dhf8r',
            'sponsor':'Sartography Pharmaceuticals',
            'ind_number':'1234',
            'user_uid':'dhf8r'
        },
        {
            'id':1,
            'title':'Requirement of hippocampal neurogenesis for the behavioral effects of soft pretzels',
            'last_updated':datetime.datetime.now(),
            'protocol_builder_status':ProtocolBuilderStatus.ACTIVE,
            'primary_investigator_id':'dhf8r',
            'sponsor':'Makerspace & Co.',
            'ind_number':'5678',
            'user_uid':'dhf8r'
        }
    ]


    @classmethod
    def setUpClass(cls):
        app.config.from_object('config.testing')
        cls.ctx = app.test_request_context()
        cls.app = app.test_client()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.drop_all()
        session.remove()
        pass

    def setUp(self):
        self.ctx.push()

    def tearDown(self):
        ExampleDataLoader.clean_db()  # This does not seem to work, some colision of sessions.
        self.ctx.pop()
        self.auths = {}

    def logged_in_headers(self, user=None, redirect_url='http://some/frontend/url'):
        if user is None:
            uid = self.test_uid
            user_info = {'uid': self.test_uid, 'first_name': 'Daniel', 'last_name': 'Funk',
                         'email_address': 'dhf8r@virginia.edu'}
        else:
            uid = user.uid
            user_info = {'uid': user.uid, 'first_name': user.first_name, 'last_name': user.last_name,
                         'email_address': user.email_address}

        query_string = self.user_info_to_query_string(user_info, redirect_url)
        rv = self.app.get("/v1.0/sso_backdoor%s" % query_string, follow_redirects=False)
        self.assertTrue(rv.status_code == 302)
        self.assertTrue(str.startswith(rv.location, redirect_url))

        user_model = session.query(UserModel).filter_by(uid=uid).first()
        self.assertIsNotNone(user_model.display_name)
        return dict(Authorization='Bearer ' + user_model.encode_auth_token().decode())

    def load_example_data(self):
        from example_data import ExampleDataLoader
        ExampleDataLoader.clean_db()
        ExampleDataLoader().load_all()

        for user_json in self.users:
            db.session.add(UserModel(**user_json))
        db.session.commit()
        for study_json in self.studies:
            study_model = StudyModel(**study_json)
            db.session.add(study_model)
            StudyService._add_all_workflow_specs_to_study(study_model)
        db.session.commit()
        db.session.flush()

        specs = session.query(WorkflowSpecModel).all()
        self.assertIsNotNone(specs)

        for spec in specs:
            files = session.query(FileModel).filter_by(workflow_spec_id=spec.id).all()
            self.assertIsNotNone(files)
            self.assertGreater(len(files), 0)

        for spec in specs:
            files = session.query(FileModel).filter_by(workflow_spec_id=spec.id).all()
            self.assertIsNotNone(files)
            self.assertGreater(len(files), 0)
            for file in files:
                file_data = session.query(FileDataModel).filter_by(file_model_id=file.id).all()
                self.assertIsNotNone(file_data)
                self.assertGreater(len(file_data), 0)

    @staticmethod
    def load_test_spec(dir_name, master_spec=False, category_id=None):
        """Loads a spec into the database based on a directory in /tests/data"""
        if session.query(WorkflowSpecModel).filter_by(id=dir_name).count() > 0:
            return
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', dir_name, "*")
        return ExampleDataLoader().create_spec(id=dir_name, name=dir_name, filepath=filepath, master_spec=master_spec,
                                               category_id=category_id)

    @staticmethod
    def protocol_builder_response(file_name):
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', 'pb_responses', file_name)
        with open(filepath, 'r') as myfile:
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

        file_model = db.session.query(FileModel).filter(FileModel.name == name).first()
        noise, file_extension = os.path.splitext(file_path)
        content_type = CONTENT_TYPES[file_extension[1:]]
        file_service.update_file(file_model, data, content_type)

    def create_workflow(self, workflow_name, study=None, category_id=None):
        if study == None:
            study = session.query(StudyModel).first()
        spec = self.load_test_spec(workflow_name, category_id=category_id)
        workflow_model = StudyService._create_workflow_model(study, spec)
        #processor = WorkflowProcessor(workflow_model)
        #workflow = session.query(WorkflowModel).filter_by(study_id=study.id, workflow_spec_id=workflow_name).first()
        return workflow_model

    def create_reference_document(self):
        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'reference', 'irb_documents.xlsx')
        file = open(file_path, "rb")
        FileService.add_reference_file(FileService.IRB_PRO_CATEGORIES_FILE,
                                       binary_data=file.read(),
                                       content_type=CONTENT_TYPES['xls'])
        file.close()

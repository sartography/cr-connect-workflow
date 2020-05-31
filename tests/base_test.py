# Set environment variable to testing before loading.
# IMPORTANT - Environment must be loaded before app, models, etc....
import os

from sqlalchemy import Sequence

os.environ["TESTING"] = "true"

import json
import unittest
import urllib.parse
import datetime

from crc.models.protocol_builder import ProtocolBuilderStatus
from crc.models.study import StudyModel
from crc.services.file_service import FileService
from crc.services.study_service import StudyService
from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel
from crc.models.user import UserModel

from crc import app, db, session
from example_data import ExampleDataLoader

#UNCOMMENT THIS FOR DEBUGGING SQL ALCHEMY QUERIES
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
        session.flush()
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
        return dict(Authorization='Bearer ' + user_model.encode_auth_token().decode())

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

        for user_json in self.users:
            db.session.add(UserModel(**user_json))
        db.session.commit()
        for study_json in self.studies:
            study_model = StudyModel(**study_json)
            db.session.add(study_model)
            StudyService._add_all_workflow_specs_to_study(study_model)
            db.session.execute(Sequence(StudyModel.__tablename__ + '_id_seq'))
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
            return session.query(WorkflowSpecModel).filter_by(id=dir_name).first()
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

    def create_user(self, uid="dhf8r", email="daniel.h.funk@gmail.com", display_name="Hoopy Frood"):
        user = session.query(UserModel).filter(UserModel.uid == uid).first()
        if user is None:
            user = UserModel(uid=uid, email_address=email, display_name=display_name)
            db.session.add(user)
            db.session.commit()
        return user

    def create_study(self, uid="dhf8r", title="Beer conception in the bipedal software engineer"):
        study = session.query(StudyModel).first()
        if study is None:
            user = self.create_user(uid=uid)
            study = StudyModel(title=title, protocol_builder_status=ProtocolBuilderStatus.ACTIVE,
                               user_uid=user.uid)
            db.session.add(study)
            db.session.commit()
        return study

    def create_workflow(self, workflow_name, study=None, category_id=None):
        db.session.flush()
        spec = db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.name == workflow_name).first()
        if spec is None:
            spec = self.load_test_spec(workflow_name, category_id=category_id)
        if study is None:
            study = self.create_study()
        workflow_model = StudyService._create_workflow_model(study, spec)
        return workflow_model

    def create_reference_document(self):
        file_path = os.path.join(app.root_path, 'static', 'reference', 'irb_documents.xlsx')
        file = open(file_path, "rb")
        FileService.add_reference_file(FileService.DOCUMENT_LIST,
                                       binary_data=file.read(),
                                       content_type=CONTENT_TYPES['xls'])
        file.close()

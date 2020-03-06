# Set environment variable to testing before loading.
# IMPORTANT - Environment must be loaded before app, models, etc....
import json
import os
import unittest
import urllib.parse

from crc.services.file_service import FileService

os.environ["TESTING"] = "true"

from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES
from crc.models.workflow import WorkflowSpecModel
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
    def load_test_spec(dir_name):
        """Loads a spec into the database based on a directory in /tests/data"""
        if session.query(WorkflowSpecModel).filter_by(id=dir_name).count() > 0:
            return
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', dir_name, "*")
        return ExampleDataLoader().create_spec(id=dir_name, name=dir_name, filepath=filepath)

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

    def assert_failure(self, rv, code=0):
        self.assertFalse(200 <= rv.status_code < 300,
                         "Incorrect Valid Response:" + rv.status + ".")
        if code != 0:
            self.assertEqual(code, rv.status_code)

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

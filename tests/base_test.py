# Set environment variable to testing before loading.
# IMPORTANT - Environment must be loaded before app, models, etc....
import json
import os
import unittest

from crc.models.file import FileModel, FileDataModel
from crc.models.workflow import WorkflowSpecModel

os.environ["TESTING"] = "true"

from crc import app, db, session
from example_data import ExampleDataLoader

# UNCOMMENT THIS FOR DEBUGGING SQL ALCHEMY QUERIES
# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)





# Great class to inherit from, as it sets up and tears down
# classes efficiently when we have a database in place.
class BaseTest(unittest.TestCase):

    auths = {}

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

    def load_test_spec(self, dir_name):
        """Loads a spec into the database based on a directory in /tests/data"""
        if session.query(WorkflowSpecModel).filter_by(id=dir_name).count() > 0:
            return
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', dir_name, "*")
        models = ExampleDataLoader().create_spec(id=dir_name, name=dir_name, filepath=filepath)
        spec = None
        for model in models:
            if isinstance(model, WorkflowSpecModel):
                spec = model
            session.add(model)
            session.commit()
        session.flush()
        return spec

    def assert_success(self, rv, msg=""):
        try:
            data = json.loads(rv.get_data(as_text=True))
            self.assertTrue(rv.status_code >= 200 and rv.status_code < 300,
                            "BAD Response: %i. \n %s" %
                            (rv.status_code, json.dumps(data)) + ". " + msg)
        except:
            self.assertTrue(rv.status_code >= 200 and rv.status_code < 300,
                            "BAD Response: %i." % rv.status_code + ". " + msg)

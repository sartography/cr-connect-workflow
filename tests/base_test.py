# Set environment variable to testing before loading.
# IMPORTANT - Environment must be loaded before app, models, etc....
import json
import os
os.environ["TESTING"] = "true"

from crc import app, db


# UNCOMMENT THIS FOR DEBUGGING SQL ALCHEMY QUERIES
# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


def clean_db():
    db.session.flush() # Clear out any transactions before deleting it all to avoid spurious errors.
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.flush()


# Great class to inherit from, as it sets up and tears down
# classes efficiently when we have a database in place.
class BaseTest:

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
        db.session.remove()
        pass

    def setUp(self):
        self.ctx.push()

    def tearDown(self):
        clean_db()  # This does not seem to work, some colision of sessions.
        self.ctx.pop()
        self.auths = {}

    def load_example_data(self):
        clean_db()
        from example_data import ExampleDataLoader
        ExampleDataLoader().load_all()

    def assert_success(self, rv, msg=""):
        try:
            data = json.loads(rv.get_data(as_text=True))
            self.assertTrue(rv.status_code >= 200 and rv.status_code < 300,
                            "BAD Response: %i. \n %s" %
                            (rv.status_code, json.dumps(data)) + ". " + msg)
        except:
            self.assertTrue(rv.status_code >= 200 and rv.status_code < 300,
                            "BAD Response: %i." % rv.status_code + ". " + msg)

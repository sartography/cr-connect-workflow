from app import app

# Great class to inherit from, as it sets up and tears down
# classes efficiently when we have a database in place.
class BaseTest:

    auths = {}

    @classmethod
    def setUpClass(cls):
        app.config.from_object('config.testing')
        cls.ctx = app.test_request_context()
        cls.app = app.test_client()
        # Great place to do a db.create_all()

    @classmethod
    def tearDownClass(cls):
        # Create place to clear everything out ...
        # db.drop_all()
        # db.session.remove()
        # elastic_index.clear()
        pass

    def setUp(self):
        self.ctx.push()

    def tearDown(self):
        # db.session.rollback()
        # Most efficient thing here is to delete all rows from
        # the database with a clear db method like this one:
        # def clean_db(db):
        #    for table in reversed(db.metadata.sorted_tables):
        #        db.session.execute(table.delete())
        # clean_db(db)
        self.ctx.pop()
        self.auths = {}


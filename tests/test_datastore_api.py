import json
from profile import Profile

from tests.base_test import BaseTest

from datetime import datetime, timezone
from unittest.mock import patch
from crc.models.data_store import DataStoreModel, DataStoreSchema
from crc.models.file import FileModel
from crc import session, app




class DataStoreTest(BaseTest):
    TEST_STUDY_ITEM = {
        "key": "MyKey",
        "workflow_id": 12,
        "study_id": 42,
        "task_id": "MyTask",
        "spec_id": "My Spec Name",
        "value": "Some Value"
    }
    TEST_FILE_ITEM = {
        "key": "MyKey",
        "workflow_id": 12,
        "task_id": "MyTask",
        "spec_id": "My Spec Name",
        "value": "Some Value"
    }

    def add_test_study_data(self):
        study_data = DataStoreSchema().dump(self.TEST_STUDY_ITEM)
        rv = self.app.post('/v1.0/datastore',
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(study_data))
        self.assert_success(rv)
        return json.loads(rv.get_data(as_text=True))

    def add_test_user_data(self):
        study_data = DataStoreSchema().dump(self.TEST_STUDY_ITEM)
        study_data['user_id'] = 'dhf8r'
        del(study_data['study_id'])
        study_data['value'] = 'User Value'
        rv = self.app.post('/v1.0/datastore',
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(study_data))
        self.assert_success(rv)
        return json.loads(rv.get_data(as_text=True))

    def add_test_file_data(self):
        file_data = DataStoreSchema().dump(self.TEST_FILE_ITEM)
        test_file = session.query(FileModel).first()
        file_data['file_id'] = test_file.id
        file_data['value'] = 'Some File Data Value'
        rv = self.app.post('/v1.0/datastore',
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(file_data))
        self.assert_success(rv)
        return json.loads(rv.get_data(as_text=True))

    def test_get_study_data(self):
        """Generic test, but pretty detailed, in that the study should return a categorized list of workflows
        This starts with out loading the example data, to show that all the bases are covered from ground 0."""

        """NOTE:  The protocol builder is not enabled or mocked out.  As the master workflow (which is empty),
        and the test workflow do not need it, and it is disabled in the configuration."""
        self.load_example_data()
        new_study = self.add_test_study_data()
        new_study = session.query(DataStoreModel).filter_by(id=new_study["id"]).first()

        api_response = self.app.get('/v1.0/datastore/%i' % new_study.id,
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        d = api_response.get_data(as_text=True)
        study_data = DataStoreSchema().loads(d)

        self.assertEqual(study_data.key, self.TEST_STUDY_ITEM['key'])
        self.assertEqual(study_data.value, self.TEST_STUDY_ITEM['value'])
        self.assertEqual(study_data.user_id, None)

    def test_update_datastore(self):
        self.load_example_data()
        new_study = self.add_test_study_data()
        new_study = session.query(DataStoreModel).filter_by(id=new_study["id"]).first()
        new_study.value = 'MyNewValue'
        api_response = self.app.put('/v1.0/datastore/%i' % new_study.id,
                                    data=DataStoreSchema().dumps(new_study),
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)

        api_response = self.app.get('/v1.0/datastore/%i' % new_study.id,
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        study_data = DataStoreSchema().loads(api_response.get_data(as_text=True))

        self.assertEqual(study_data.key, self.TEST_STUDY_ITEM['key'])
        self.assertEqual(study_data.value, 'MyNewValue')
        self.assertEqual(study_data.user_id, None)

    def test_delete_datastore(self):
        self.load_example_data()
        new_study = self.add_test_study_data()
        oldid = new_study['id']
        new_study = session.query(DataStoreModel).filter_by(id=new_study["id"]).first()
        rv = self.app.delete('/v1.0/datastore/%i' % new_study.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        studyreponse = session.query(DataStoreModel).filter_by(id=oldid).first()
        self.assertEqual(studyreponse,None)

    def test_data_crosstalk(self):
        """Test to make sure that data saved for user or study is not accessible from the other method"""

        self.load_example_data()
        new_study = self.add_test_study_data()
        new_user = self.add_test_user_data()

        api_response = self.app.get(f'/v1.0/datastore/user/{new_user["user_id"]}',
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        d = json.loads(api_response.get_data(as_text=True))
        self.assertEqual(d[0]['value'],'User Value')

        api_response = self.app.get(f'/v1.0/datastore/study/{new_study["study_id"]}',
                                    headers=self.logged_in_headers(), content_type="application/json")

        self.assert_success(api_response)
        d = json.loads(api_response.get_data(as_text=True))
        self.assertEqual(d[0]['value'],'Some Value')

    def test_datastore_user(self):
        self.load_example_data()
        new_user = self.add_test_user_data()
        api_response = self.app.get(f'/v1.0/datastore/user/{new_user["user_id"]}',
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        data = json.loads(api_response.get_data(as_text=True))

        print('test_datastore_user')

    def test_datastore_study(self):
        self.load_example_data()
        new_study = self.add_test_study_data()
        api_response = self.app.get(f'/v1.0/datastore/study/{new_study["study_id"]}',
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        data = json.loads(api_response.get_data(as_text=True))

        print('test_datastore_study')

    def test_datastore_file(self):
        self.load_example_data()
        new_file = self.add_test_file_data()
        api_response = self.app.get(f'/v1.0/datastore/file/{new_file["file_id"]}',
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        data = json.loads(api_response.get_data(as_text=True))
        self.assertEqual('MyKey', data[0]['key'])
        self.assertEqual('Some File Data Value', data[0]['value'])

        print('test_datastore_file')

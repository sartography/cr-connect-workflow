from tests.base_test import BaseTest
from crc import session
from crc.models.data_store import DataStoreModel
from io import BytesIO


class TestDeleteTaskFileData(BaseTest):

    def test_delete_task_file_data(self):
        self.load_example_data()
        workflow = self.create_workflow('delete_task_file_data')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        correct_name = first_task.form['fields'][0]['id']
        data = {'file': (BytesIO(b"abcdef"), 'test_file.txt')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, first_task.name, correct_name), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_id = rv.json['id']
        self.complete_form(workflow, first_task, {'Study_Protocol_Document': {'id': file_id},
                                                  'ProtocolVersionDate': '20210721'})
        data_store = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id).first()
        self.assertEqual('ProtocolVersionDate', data_store.key)
        self.assertEqual('20210721', data_store.value)

        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.complete_form(workflow, second_task, {})

        workflow_api = self.get_workflow_api(workflow)
        third_task = workflow_api.next_task
        self.complete_form(workflow, third_task, {})
        workflow_api = self.get_workflow_api(workflow)

        data_store = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id).first()
        self.assertEqual(None, data_store)

        print('test_delete_task_file_data')

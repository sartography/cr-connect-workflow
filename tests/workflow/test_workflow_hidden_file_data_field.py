from tests.base_test import BaseTest
from io import BytesIO
import json


class TestHiddenFileDataField(BaseTest):

    def test_hidden_file_data_field(self):

        self.load_example_data()
        workflow = self.create_workflow('hidden_file_data_field')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.complete_form(workflow, task, {'hide_field': True})
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        data = {'file': (BytesIO(b"abcdef"), 'test_file.txt')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_id=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.id, 'Study_App_Doc'), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_id = json.loads(rv.get_data())['id']

        self.complete_form(workflow, task, {'UploadFile': {'id': file_id},
                                            'Name': 'Some Name String'})
        workflow_api = self.get_workflow_api(workflow)
        new_task = workflow_api.next_task
        self.assertEqual('Activity_ViewData', new_task.name)
        self.assertEqual('Some Name String', new_task.data['Name'])
        self.assertNotIn('ExtraField', new_task.data)

    def test_not_hidden_file_data_field(self):

        self.load_example_data()
        workflow = self.create_workflow('hidden_file_data_field')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.complete_form(workflow, task, {'hide_field': False})
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        data = {'file': (BytesIO(b"abcdef"), 'test_file.txt')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_id=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.id, 'Study_App_Doc'), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_id = json.loads(rv.get_data())['id']

        self.complete_form(workflow, task, {'UploadFile': {'id': file_id},
                                            'Name': 'Some Name String',
                                            'ExtraField': 'Some Extra String'})
        workflow_api = self.get_workflow_api(workflow)
        new_task = workflow_api.next_task
        self.assertEqual('Activity_ViewData', new_task.name)
        self.assertEqual('Some Name String', new_task.data['Name'])
        self.assertIn('ExtraField', new_task.data)
        self.assertEqual('Some Extra String', new_task.data['ExtraField'])

import json
from tests.base_test import BaseTest
from crc.services.file_service import FileService


class TestDocumentDirectories(BaseTest):

    def test_directory_list(self):
        self.load_example_data()
        irb_code_1 = 'UVACompl_PRCAppr'
        irb_code_2 = 'Study_App_Doc'

        workflow = self.create_workflow('empty_workflow')
        first_task = self.get_workflow_api(workflow).next_task
        study_id = workflow.study_id

        # Add a file
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      task_spec_name=first_task.name,
                                      name="something.png", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code_1)
        # Add second file
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      task_spec_name=first_task.name,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code=irb_code_2)

        # Get back the list of documents and their directories.
        rv = self.app.get('/v1.0/document_directory/%i' % study_id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        print(json_data)
        self.assertEqual(2, len(json_data))
        self.assertEqual('UVA Compliance', json_data[0]['level'])
        self.assertEqual('PRC Approval', json_data[0]['children'][0]['level'])
        self.assertEqual('something.png', json_data[0]['children'][0]['children'][0]['file']['name'])
        self.assertEqual('Study', json_data[1]['level'])
        self.assertEqual('Application', json_data[1]['children'][0]['level'])
        self.assertEqual('Document', json_data[1]['children'][0]['children'][0]['level'])
        self.assertEqual('anything.png',  json_data[1]['children'][0]['children'][0]['children'][0]['file']['name'])

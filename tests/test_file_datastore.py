from tests.base_test import BaseTest

from crc import db
from crc.models.data_store import DataStoreModel
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor

from io import BytesIO

import json


class TestFileDatastore(BaseTest):

    def test_file_datastore_workflow(self):
        self.load_example_data()
        self.create_reference_document()
        # we need to create a file with an IRB code
        # for this study
        workflow = self.create_workflow('file_data_store')
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code)

        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task_data = processor.bpmn_workflow.last_task.data
        self.assertTrue(str(task_data['fileid']) in task_data['fileurl'])
        self.assertEqual(task_data['filename'],'anything.png')
        self.assertEqual(task_data['output'], 'me')
        self.assertEqual(task_data['output2'], 'nope')

    def test_file_data_store_file_data_property(self):
        self.load_example_data()
        workflow = self.create_workflow('enum_file_data')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        # upload the file
        correct_name = task.form['fields'][1]['id']
        data = {'file': (BytesIO(b"abcdef"), 'test_file.txt')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_id=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.id, correct_name), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_id = json.loads(rv.get_data())['id']

        # process the form that sets the datastore values
        self.complete_form(workflow, task, {'Study_App_Doc': {'id': file_id},
                                                     'IRB_HSR_Application_Type': {'label': 'Expedited Application'}})

        # assert the data_store was set correctly
        data_store = db.session.query(DataStoreModel).filter(DataStoreModel.file_id==file_id).first()
        self.assertEqual('IRB_HSR_Application_Type', data_store.key)
        self.assertEqual('Expedited Application', data_store.value)

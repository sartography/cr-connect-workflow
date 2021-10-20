import unittest
from tests.base_test import BaseTest
import json
import os
import copy

from docxtpl import Listing
from io import BytesIO

from crc import app
from crc.scripts.complete_template import CompleteTemplate
from crc.services.jinja_service import JinjaService


class TestCompleteTemplate(unittest.TestCase):

    def test_rich_text_update(self):
        script = CompleteTemplate()
        data = {"name": "Dan"}
        data_copy = copy.deepcopy(data)
        script.rich_text_update(data_copy)
        self.assertEqual(data, data_copy)

    def test_rich_text_update_new_line(self):
        script = CompleteTemplate()
        data = {"name": "Dan\n Funk"}
        data_copy = copy.deepcopy(data)
        script.rich_text_update(data_copy)
        self.assertNotEqual(data, data_copy)
        self.assertIsInstance(data_copy["name"], Listing)

    def test_rich_text_nested_new_line(self):
        script = CompleteTemplate()
        data = {"names": [{"name": "Dan\n Funk"}]}
        data_copy = copy.deepcopy(data)
        script.rich_text_update(data_copy)
        self.assertNotEqual(data, data_copy)
        self.assertIsInstance(data_copy["names"][0]["name"], Listing)


class TestCallingScript(BaseTest):

    def test_calling_script(self):
        workflow = self.create_workflow('docx')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        filepath = os.path.join(app.root_path, '..', 'tests', 'data', 'docx', 'Letter.docx')
        with open(filepath, 'rb') as f:
            file_data = {'file': (f, 'Letter.docx')}

        template_data = {'fullname',
                'date',
                'title',
                'company',
                'lastname'}

        data = {'file': (BytesIO(b"abcdef"), 'Letter.docx')}

        FileService.add_workflow_file(workflow_id=workflow_id,
                                      task_spec_name=task.get_name(),
                                      name=file_name,
                                      content_type=CONTENT_TYPES['docx'],
                                      binary_data=final_document_stream.read(),
                                      irb_doc_code=irb_doc_code)



        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.name, 'Study_App_Doc'),
                           data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data',
                           headers=self.logged_in_headers())


        workflow_api = self.complete_form(workflow, task, )

        print('test_calling_script')

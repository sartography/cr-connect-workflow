import unittest
from tests.base_test import BaseTest
import copy
import docx

from docxtpl import Listing
from io import BytesIO

from crc import session
from crc.models.file import FileModel
from crc.services.jinja_service import JinjaService


class TestCompleteTemplate(unittest.TestCase):

    def test_rich_text_update(self):
        script = JinjaService()
        data = {"name": "Dan"}
        data_copy = copy.deepcopy(data)
        script.rich_text_update(data_copy)
        self.assertEqual(data, data_copy)

    def test_rich_text_update_new_line(self):
        script = JinjaService()
        data = {"name": "Dan\n Funk"}
        data_copy = copy.deepcopy(data)
        script.rich_text_update(data_copy)
        self.assertNotEqual(data, data_copy)
        self.assertIsInstance(data_copy["name"], Listing)

    def test_rich_text_nested_new_line(self):
        script = JinjaService()
        data = {"names": [{"name": "Dan\n Funk"}]}
        data_copy = copy.deepcopy(data)
        script.rich_text_update(data_copy)
        self.assertNotEqual(data, data_copy)
        self.assertIsInstance(data_copy["names"][0]["name"], Listing)


class TestEmbeddedTemplate(BaseTest):

    def run_docx_embedded_workflow(self, data):
        self.create_reference_document()
        workflow = self.create_workflow('docx_embedded')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.complete_form(workflow, task, data)
        return workflow_api

    def test_embedded_template(self):
        data = {'include_me': 'Hello {{ name }}!',
                'name': 'World',
                'template_file_name': 'simple.docx',
                'irb_doc_code': 'Study_App_Doc'}
        workflow_api = self.run_docx_embedded_workflow(data)

        # Get the file data created for us in the workflow
        file_model = session.query(FileModel).\
            filter(FileModel.workflow_id == workflow_api.id).\
            filter(FileModel.irb_doc_code == 'Study_App_Doc').\
            first()
        # If we don't pass file_name, name should be set to template_file_name
        self.assertEqual(data['template_file_name'], file_model.name)

        # read the data as a word document
        document = docx.Document(BytesIO(file_model.data))
        # Make sure 'Hello World!' is there
        self.assertEqual('Hello World!', document.paragraphs[4].text)

        data = {'include_me': 'Hello {{ name }}!',
                'name': 'World',
                'template_file_name': 'simple.docx',
                'irb_doc_code': 'Study_App_Doc',
                'file_name': 'test_file_name.docx'}
        workflow_api = self.run_docx_embedded_workflow(data)

        file_model = session.query(FileModel).\
            filter(FileModel.workflow_id == workflow_api.id).\
            filter(FileModel.irb_doc_code == 'Study_App_Doc').\
            first()
        # If we do pass file_name, name should be set to file_name
        self.assertEqual(data['file_name'], file_model.name)

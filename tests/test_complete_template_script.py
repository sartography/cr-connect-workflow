import unittest
from tests.base_test import BaseTest
import copy
import docx

from docxtpl import Listing
from io import BytesIO

from crc import session
from crc.models.file import DocumentModel
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

    def test_embedded_template(self):
        self.create_reference_document()
        workflow = self.create_workflow('docx_embedded')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        data = {'include_me': 'Hello {{ name }}!',
                'name': 'World',
                'file_name': 'simple.docx',
                'irb_doc_code': 'Study_App_Doc'}
        self.complete_form(workflow, task, data)

        # Get the file data created for us in the workflow
        file_model = session.query(DocumentModel).\
            filter(DocumentModel.workflow_id == workflow.id).\
            filter(DocumentModel.irb_doc_code == 'Study_App_Doc').\
            first()
        # file_data_model = session.query(FileDataModel). \
        #     filter(FileDataModel.file_model_id == file_model.id).\
        #     first()

        # read the data as a word document
        document = docx.Document(BytesIO(file_model.data))
        # Make sure 'Hello World!' is there
        self.assertEqual('Hello World!', document.paragraphs[4].text)

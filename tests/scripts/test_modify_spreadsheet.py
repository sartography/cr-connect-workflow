from tests.base_test import BaseTest

from crc import app, session
from crc.models.file import DocumentModel
from crc.services.user_file_service import UserFileService

from io import BytesIO
from openpyxl import load_workbook

import os


class TestModifySpreadsheet(BaseTest):

    def upload_spreadsheet(self, workflow, task, irb_doc_code):
        filepath = os.path.join(app.root_path, '..', 'tests', 'data',
                                'modify_spreadsheet', 'test_spreadsheet.xlsx')
        with open(filepath, 'br') as f_open:
            ss_data = f_open.read()

        file_model = UserFileService.add_workflow_file(workflow_id=workflow.id,
                                                       task_spec_name=task.name,
                                                       name="test_spreadsheet.xlsx", content_type="text",
                                                       binary_data=ss_data, irb_doc_code=irb_doc_code)
        workflow_api = self.complete_form(workflow, task, {irb_doc_code: {'id': file_model.id}})
        return workflow_api

    @staticmethod
    def get_sheet(workflow_id, irb_doc_code):
        spreadsheet = session.query(DocumentModel). \
            filter(DocumentModel.workflow_id == workflow_id). \
            filter(DocumentModel.irb_doc_code == irb_doc_code). \
            first()
        workbook = load_workbook(BytesIO(spreadsheet.data))
        sheet = workbook.active
        return sheet

    def test_modify_spreadsheet(self):
        irb_doc_code = 'Finance_BCA'
        cell_indicator = 'C4'
        input_text = 'This is my input text.'

        workflow = self.create_workflow('modify_spreadsheet')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.upload_spreadsheet(workflow, task, irb_doc_code)

        sheet = self.get_sheet(workflow.id, irb_doc_code)
        self.assertEqual(None, sheet[cell_indicator].value)

        task = workflow_api.next_task
        self.complete_form(workflow, task, {'cell_indicator': cell_indicator,
                                            'input_text': input_text})

        sheet = self.get_sheet(workflow.id, irb_doc_code)
        self.assertEqual(input_text, sheet[cell_indicator].value)

    def test_missing_spreadsheet(self):
        """The modify_spreadsheet has Finance_BCA hard-coded as the spreadsheet to modify.
        In this test we upload a spreadsheet with a different doc code,
        and assert that we raise an error when the Finance_BCA spreadsheet does not exist"""
        irb_doc_code = 'Finance_GPRF'
        cell_indicator = 'C4'
        input_text = 'This is my input text.'

        workflow = self.create_workflow('modify_spreadsheet')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.upload_spreadsheet(workflow, task, irb_doc_code)
        task = workflow_api.next_task
        with self.assertRaises(AssertionError):
            self.complete_form(workflow, task, {'cell_indicator': cell_indicator,
                                                'input_text': input_text})

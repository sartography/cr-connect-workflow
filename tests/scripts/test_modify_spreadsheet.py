from tests.base_test import BaseTest

from crc import app, session
from crc.models.file import FileModel, FileDataModel
from crc.services.user_file_service import UserFileService

from io import BytesIO
from openpyxl import load_workbook

import os


class TestModifySpreadsheet(BaseTest):

    @staticmethod
    def get_sheet(workflow_id, irb_doc_code):
        spreadsheet = session.query(FileModel). \
            filter(FileModel.workflow_id == workflow_id). \
            filter(FileModel.irb_doc_code == irb_doc_code). \
            first()
        spreadsheet_data = session.query(FileDataModel). \
            filter(FileDataModel.file_model_id == spreadsheet.id). \
            first()
        workbook = load_workbook(BytesIO(spreadsheet_data.data))
        sheet = workbook.active
        return sheet

    def test_modify_spreadsheet(self):
        irb_doc_code = 'Finance_BCA'
        cell_indicator = 'C4'
        input_text = 'This is my input text.'

        workflow = self.create_workflow('modify_spreadsheet')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        filepath = os.path.join(app.root_path, '..', 'tests', 'data',
                                'modify_spreadsheet', 'test_spreadsheet.xlsx')
        with open(filepath, 'br') as f_open:
            ss_data = f_open.read()

        file_model = UserFileService.add_workflow_file(workflow_id=workflow.id,
                                                       task_spec_name=task.name,
                                                       name="test_spreadsheet.xlsx", content_type="text",
                                                       binary_data=ss_data, irb_doc_code=irb_doc_code)
        workflow_api = self.complete_form(workflow, task, {irb_doc_code: {'id': file_model.id}})

        sheet = self.get_sheet(workflow.id, irb_doc_code)
        self.assertEqual(None, sheet[cell_indicator].value)

        task = workflow_api.next_task
        self.complete_form(workflow, task, {'cell_indicator': cell_indicator,
                                            'input_text': input_text})

        sheet = self.get_sheet(workflow.id, irb_doc_code)
        self.assertEqual(input_text, sheet[cell_indicator].value)

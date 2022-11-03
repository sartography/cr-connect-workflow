from tests.base_test import BaseTest

from crc import app, session
from crc.models.file import FileModel
from crc.services.user_file_service import UserFileService

from io import BytesIO
from openpyxl import load_workbook

import os


class TestModifySpreadsheet(BaseTest):

    irb_doc_code = 'Finance_BCA'
    cell_indicator = 'C4'
    input_text = 'This is my input text.'

    def upload_spreadsheet(self, workflow, task, irb_doc_code, spreadsheet_name='test_spreadsheet.xlsx'):
        filepath = os.path.join(app.root_path, '..', 'tests', 'data',
                                'modify_spreadsheet', spreadsheet_name)
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
        spreadsheet = session.query(FileModel). \
            filter(FileModel.workflow_id == workflow_id). \
            filter(FileModel.irb_doc_code == irb_doc_code). \
            filter(FileModel.archived == False). \
            first()
        workbook = load_workbook(BytesIO(spreadsheet.data))
        sheet = workbook.active
        return sheet

    def test_modify_spreadsheet(self):

        workflow = self.create_workflow('modify_spreadsheet')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.upload_spreadsheet(workflow, task, self.irb_doc_code)

        sheet = self.get_sheet(workflow.id, self.irb_doc_code)
        self.assertEqual(None, sheet[self.cell_indicator].value)

        task = workflow_api.next_task
        self.complete_form(workflow, task, {'cell_indicator': self.cell_indicator,
                                            'input_text': self.input_text})

        sheet = self.get_sheet(workflow.id, self.irb_doc_code)
        self.assertEqual(self.input_text, sheet[self.cell_indicator].value)

    def test_modify_spreadsheet_multiple_versions_of_spreadsheet(self):
        """This test ensures that we get the correct version of the spreadsheet if multiple versions are uploaded.
        I.e., we get the current version and not any archived versions
        """
        workflow = self.create_workflow('modify_spreadsheet')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.upload_spreadsheet(workflow, task, self.irb_doc_code, 'test_spreadsheet.xlsx')
        files = FileModel.query\
            .filter(FileModel.workflow_id == workflow.id)\
            .filter(FileModel.irb_doc_code == self.irb_doc_code)\
            .all()
        assert len(files) == 1
        assert files[0].archived is False
        UserFileService().delete_file(files[0].id)

        workflow_api = self.restart_workflow_api(workflow)
        task = workflow_api.next_task
        assert task.name == "Activity_FileUpload"
        workflow_api = self.upload_spreadsheet(workflow, task, self.irb_doc_code, 'test_spreadsheet_2.xlsx')
        files = FileModel.query\
            .filter(FileModel.workflow_id == workflow.id)\
            .filter(FileModel.irb_doc_code == self.irb_doc_code)\
            .all()
        assert len(files) == 2
        assert files[0].archived is True
        assert files[1].archived is False

        task = workflow_api.next_task
        assert task.name == "Activity_GetModifyData"

        data = {"cell_indicator": "B4", "input_text": "Just some text"}
        self.complete_form(workflow, task, data)

        sheet = self.get_sheet(workflow.id, self.irb_doc_code)
        self.assertEqual("Just some text", sheet["B4"].value)

    def test_missing_spreadsheet(self):
        """The modify_spreadsheet has Finance_BCA hard-coded as the spreadsheet to modify.
        In this test we upload a spreadsheet with a different doc code,
        and assert that we raise an error when the Finance_BCA spreadsheet does not exist"""
        irb_doc_code = 'Finance_GPRF'

        workflow = self.create_workflow('modify_spreadsheet')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.upload_spreadsheet(workflow, task, irb_doc_code)
        task = workflow_api.next_task
        with self.assertRaises(AssertionError):
            self.complete_form(workflow, task, {'cell_indicator': self.cell_indicator,
                                                'input_text': self.input_text})

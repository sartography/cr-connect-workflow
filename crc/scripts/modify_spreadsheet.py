from crc import session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel
from crc.scripts.script import Script

from io import BytesIO
from openpyxl import load_workbook
from openpyxl.writer.excel import save_virtual_workbook


class ModifySpreadsheet(Script):

    @staticmethod
    def get_parameters(args, kwargs):
        parameters = {}
        if len(args) == 4 or ('upload_workflow_id' in kwargs and 'irb_doc_code' in kwargs and 'cell' in kwargs and 'text' in kwargs):
            if 'upload_workflow_id' in kwargs and 'irb_doc_code' in kwargs and 'line' in kwargs and 'text' in kwargs:
                parameters['upload_workflow_id'] = (kwargs['upload_workflow_id'])
                parameters['irb_doc_code'] = (kwargs['irb_doc_code'])
                parameters['cell'] = (kwargs['cell'])
                parameters['text'] = (kwargs['text'])
            else:
                parameters['upload_workflow_id'] = (args[0])
                parameters['irb_doc_code'] = (args[1])
                parameters['cell'] = (args[2])
                parameters['text'] = (args[3])
        return parameters

    def get_description(self):
        return """Script to modify an existing spreadsheet. 
        It inserts text into a spreadsheet in the cell indicated.
        Requires 'upload_workflow_id', 'irb_doc_code', 'cell', and 'text' parameters.
        Example: modify_spreadsheet(1234, 'Finance_BCA', 'C4', 'This is my inserted text')
        Example: modify_spreadsheet(upload_workflow_id=1234, irb_doc_code='Finance_BCA', cell='C4', text='This is my inserted text')
        """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        parameters = self.get_parameters(args, kwargs)
        if len(parameters) == 4:
            return parameters
        else:
            raise ApiError(code='missing_parameters',
                           message='The modify_spreadsheet script requires 4 parameters: upload_workflow_id, irb_doc_code, cell, and text')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        parameters = self.get_parameters(args, kwargs)
        if len(parameters) == 4:

            spreadsheet = session.query(FileModel). \
                filter(FileModel.workflow_id == parameters['upload_workflow_id']). \
                filter(FileModel.irb_doc_code == parameters['irb_doc_code']).\
                first()
            spreadsheet_data = session.query(FileDataModel).\
                filter(FileDataModel.file_model_id==spreadsheet.id).\
                first()
            workbook = load_workbook(BytesIO(spreadsheet_data.data))
            sheet = workbook.active
            sheet[parameters['cell']] = parameters['text']
            data_string = save_virtual_workbook(workbook)
            spreadsheet_data.data = data_string
            session.commit()
            return parameters
        else:
            raise ApiError(code='missing_parameters',
                           message='The modify_spreadsheet script requires 4 parameters: upload_workflow_id, irb_doc_code, cell, and text')

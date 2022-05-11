from crc import session
from flask_bpmn.api.api_error import ApiError
from crc.models.file import FileModel
from crc.scripts.script import Script

from io import BytesIO
from openpyxl import load_workbook
from openpyxl.writer.excel import save_virtual_workbook


class ModifySpreadsheet(Script):

    @staticmethod
    def get_parameters(args, kwargs):
        parameters = {}
        if len(args) == 3 or ('irb_doc_code' in kwargs and 'cell' in kwargs and 'text' in kwargs):
            if 'irb_doc_code' in kwargs and 'cell' in kwargs and 'text' in kwargs:
                parameters['irb_doc_code'] = (kwargs['irb_doc_code'])
                parameters['cell'] = (kwargs['cell'])
                parameters['text'] = (kwargs['text'])
            else:
                parameters['irb_doc_code'] = (args[0])
                parameters['cell'] = (args[1])
                parameters['text'] = (args[2])
        return parameters

    def get_description(self):
        return """Script to modify an existing spreadsheet. 
        It inserts text into a spreadsheet in the cell indicated.
        Requires 'irb_doc_code', 'cell', and 'text' parameters.
        Example: modify_spreadsheet('Finance_BCA', 'C4', 'This is my inserted text')
        Example: modify_spreadsheet(irb_doc_code='Finance_BCA', cell='C4', text='This is my inserted text')
        """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        parameters = self.get_parameters(args, kwargs)
        if len(parameters) == 3:
            return True
        else:
            raise ApiError(code='missing_parameters',
                           message='The modify_spreadsheet script requires 3 parameters: irb_doc_code, cell, and text')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        parameters = self.get_parameters(args, kwargs)
        if len(parameters) == 3:

            spreadsheet = session.query(FileModel). \
                filter(FileModel.workflow_id == workflow_id). \
                filter(FileModel.irb_doc_code == parameters['irb_doc_code']).\
                first()
            if spreadsheet:
                workbook = load_workbook(BytesIO(spreadsheet.data))
                sheet = workbook.active
                sheet[parameters['cell']] = parameters['text']
                data_string = save_virtual_workbook(workbook)
                spreadsheet.data = data_string
                session.commit()
            else:
                raise ApiError(code='missing_spreadsheet',
                               message=f"The spreadshhet you want to modify does not exist. Workflow ID is {workflow_id}, and IRB Doc Code is {parameters['irb_doc_code']}")
        else:
            raise ApiError(code='missing_parameters',
                           message='The modify_spreadsheet script requires 3 parameters: irb_doc_code, cell, and text')

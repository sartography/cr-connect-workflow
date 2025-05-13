from crc.scripts.script import Script
from crc.services.spreadsheet_service import SpreadsheetService

class GetHIPAAIdentifiers(Script):

    def get_description(self):
        return """This is my description"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        spreadsheet_name = 'HIPAA_Ids.xlsx'
        hipaa_dict = SpreadsheetService().create_enum_dict_from_spreadsheet(spreadsheet_name)
        return hipaa_dict

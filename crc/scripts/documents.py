from crc.api.common import ApiError
from crc.scripts.script import Script, ScriptValidationError
from crc.services.file_service import FileService
from crc.services.protocol_builder import ProtocolBuilderService


class Documents(Script):
    """Provides information about the documents required by Protocol Builder."""
    pb = ProtocolBuilderService()

    def get_description(self):
        return """
Provides detailed information about the documents loaded as a part of completing tasks.
Makes an immediate call to the IRB Protocol Builder API to get a list of currently required
documents.  It then collects all the information in a reference file called 'irb_pro_categories.xls',
if the Id from Protocol Builder matches an Id in this table, all data available in that row
is also provided.

This place a dictionary of values in the current task, where the key is the code in the lookup table.

For example:
``` "Documents" :
   {
     "UVACompliance_PRCApproval": {
            "name": "Cancer Center's PRC Approval Form",
            "category1": "UVA Compliance",
            "category2": "PRC Approval",
            "category3": "",
            "Who Uploads?": "CRC",
            "required": True,
            "Id": 6
            "count": 0
        },
     24: { ...
        }
```            
"""
    def do_task_validate_only(self, task, study_id, *args, **kwargs):
        """For validation only, pretend no results come back from pb"""
        pb_docs = []
        self.add_data_to_task(task, self.get_documents(study_id, pb_docs))

    def do_task(self, task, study_id, *args, **kwargs):
        """Takes data from the protocol builder, and merges it with data from the IRB Pro Categories
         spreadsheet to return pertinent details about the required documents."""
        pb_docs = self.pb.get_required_docs(study_id, as_objects=True)
        self.add_data_to_task(task, self.get_documents(study_id, pb_docs))

    def get_documents(self, study_id, pb_docs):
        """Takes data from the protocol builder, and merges it with data from the IRB Pro Categories spreadsheet to return
        pertinent details about the required documents."""

        doc_dictionary = FileService.get_file_reference_dictionary()
        required_docs = {}
        for code, required_doc in doc_dictionary.items():
            try:
                pb_data = next((item for item in pb_docs if int(item.AUXDOCID) == int(required_doc['Id'])), None)
            except:
                pb_data = None
            required_doc['count'] = self.get_count(study_id, code)
            required_doc['required'] = False
            if pb_data:
                required_doc['required'] = True
            required_docs[code] = required_doc
        return required_docs

    def get_count(self, study_id, irb_doc_code):
        """Returns the total number of documents that have been uploaded that match
        the given document id. """
        return(len(FileService.get_files(study_id=study_id, irb_doc_code=irb_doc_code)))

    # Verifies that information is available for this script task to function
    # correctly. Returns a list of validation errors.
    @staticmethod
    def validate():
        errors = []
        try:
            dict = FileService.get_file_reference_dictionary()
        except ApiError as ae:
            errors.append(ScriptValidationError.from_api_error(ae))
        return errors

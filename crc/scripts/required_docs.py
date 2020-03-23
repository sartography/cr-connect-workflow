from pandas import ExcelFile

from crc import session, ma
from crc.api.common import ApiError
from crc.models.study import StudyModel, StudyModelSchema
from crc.scripts.script import Script, ScriptValidationError
from crc.services.file_service import FileService
from crc.services.protocol_builder import ProtocolBuilderService


class RequiredDocs(Script):
    """Provides information about the documents required by Protocol Builder."""
    pb = ProtocolBuilderService()
    type_options = ['info', 'investigators', 'required_docs', 'details']

    def get_description(self):
        return """
Provides detailed information about the documents required by the Protocol Builder.
Makes an immediate call to the IRB Protocol Builder API to get a list of currently required
documents.  It then collects all the information in a reference file called 'irb_pro_categories.xls',
if the Id from Protcol Builder matches an Id in this table, all data available in that row
is also provided.

This place a dictionary of values in the current task, where the key is the numeric id.

For example:
``` "required_docs" :
   {
     6: {
            "name": "Cancer Center's PRC Approval Form",
            "category1": "UVA Compliance",
            "category2": "PRC Approval",
            "category3": "",
            "Who Uploads?": "CRC",
            "required": True,
            "upload_count": 0
        },
     24: { ...
        }
```            
"""
                    

    def do_task(self, task, study_id, *args, **kwargs):
        """Takes data from the protocol builder, and merges it with data from the IRB Pro Categories
         spreadsheet to return pertinant details about the required documents."""
        self.get_required_docs(study_id)
        task.data["required_docs"] = self.get_required_docs(study_id)

    def get_required_docs(self, study_id):
        """Takes data from the protocol builder, and merges it with data from the IRB Pro Categories spreadsheet to return
        pertinant details about the required documents."""
        pb_docs = self.pb.get_required_docs(study_id)
        doc_dictionary = FileService.get_file_reference_dictionary()
        required_docs = []
        for doc in pb_docs:
            id = int(doc['AUXDOCID'])
            required_doc = {'id': id, 'name': doc['AUXDOC'], 'required': True,
                            'count': 0}
            if id in doc_dictionary:
                required_doc = {**required_doc, **doc_dictionary[id]}
                required_doc['count'] = self.get_count(study_id, doc_dictionary[id]["Code"])
            required_docs.append(required_doc)
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

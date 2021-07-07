from crc.api.common import ApiError
from crc.models.api_models import DocumentDirectory
from crc.services.file_service import FileService
from crc.services.lookup_service import LookupService


class DocumentService(object):
    """The document service provides details about the types of documents that can be uploaded to a workflow.
    This metadata about different document types is managed in an Excel spreadsheet, which can be uploaded at any
    time to change which documents are accepted, and it allows us to categorize these documents.  At a minimum,
    the spreadsheet should contain the columns 'code', 'category1', 'category2', 'category3', 'description' and 'id',
    code is required for all rows in the table, the other fields are optional. """

    DOCUMENT_LIST = "irb_documents.xlsx"

    @staticmethod
    def is_allowed_document(code):
        doc_dict = DocumentService.get_dictionary()
        return code in doc_dict

    @staticmethod
    def verify_doc_dictionary(dd):
        """
        We are currently getting structured information from an XLS file, if someone accidentally
        changes a header we will have problems later, so we will verify we have the headers we need
        here
        """
        required_fields = ['category1', 'category2', 'category3', 'description']

        # we only need to check the first item, as all of the keys should be the same
        key = list(dd.keys())[0]
        for field in required_fields:
            if field not in dd[key].keys():
                raise ApiError(code="Invalid document list %s" % DocumentService.DOCUMENT_LIST,
                               message='Please check the headers in %s' % DocumentService.DOCUMENT_LIST)

    @staticmethod
    def get_dictionary():
        """Returns a dictionary of document details keyed on the doc_code."""
        file_data = FileService.get_reference_file_data(DocumentService.DOCUMENT_LIST)
        lookup_model = LookupService.get_lookup_model_for_file_data(file_data, 'code', 'description')
        doc_dict = {}
        for lookup_data in lookup_model.dependencies:
            doc_dict[lookup_data.value] = lookup_data.data
        return doc_dict

    @staticmethod
    def get_directory(doc_dict, files, workflow_id):
        """Returns a list of directories, hierarchically nested by category, with files at the deepest level.
        Empty directories are not include."""
        directory = []
        if files:
            for file in files:
                if file.irb_doc_code in doc_dict:
                    doc_code = doc_dict[file.irb_doc_code]
                else:
                    doc_code = {'category1': "Unknown", 'category2': None, 'category3': None}
                if workflow_id:
                    expand = file.workflow_id == int(workflow_id)
                else:
                    expand = False
                print(expand)
                categories = [x for x in [doc_code['category1'], doc_code['category2'], doc_code['category3'], file] if x]
                DocumentService.ensure_exists(directory, categories, expanded=expand)
        return directory

    @staticmethod
    def ensure_exists(output, categories, expanded):
        """
        This is a recursive function, it expects a list of
        levels with a file object at the end (kinda like duck,duck,duck,goose)

        for each level, it makes sure that level is already in the structure and if it is not
        it will add it

        function terminates upon getting an entry that is a file object ( or really anything but string)
        """
        current_item = categories[0]
        found = False
        if isinstance(current_item, str):
            for item in output:
                if item.level == current_item:
                    found = True
                    item.filecount = item.filecount + 1
                    item.expanded = expanded | item.expanded
                    DocumentService.ensure_exists(item.children, categories[1:], expanded)
            if not found:
                new_level = DocumentDirectory(level=current_item)
                new_level.filecount = 1
                new_level.expanded = expanded
                output.append(new_level)
                DocumentService.ensure_exists(new_level.children, categories[1:], expanded)
            else:
                print("Found it")
        else:
            new_level = DocumentDirectory(file=current_item)
            new_level.expanded = expanded
            output.append(new_level)

from crc.models.api_models import DocumentDirectorySchema
from crc.models.file import File
from crc.services.document_service import DocumentService
from crc.services.lookup_service import LookupService
from crc.services.user_file_service import UserFileService


def get_document_directory(study_id, workflow_id=None):
    """
    return a nested list of files arranged according to the category hierarchy
    defined in the doc dictionary
    """
    file_models = UserFileService.get_files_for_study(study_id=study_id)
    doc_dict = DocumentService.get_dictionary()
    files = (File.from_file_model(model, doc_dict) for model in file_models)
    directory = DocumentService.get_directory(doc_dict, files, workflow_id)

    return DocumentDirectorySchema(many=True).dump(directory)

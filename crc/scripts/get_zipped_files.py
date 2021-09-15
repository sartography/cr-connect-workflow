from crc import session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel
from crc.scripts.script import Script
from crc.services.file_service import FileService
from crc.services.study_service import StudyService

import os
import zipfile


class GetZippedFiles(Script):

    """This script creates a zip document from a list of file ids"""

    def get_description(self):
        """Creates a zip file from a list of file_ids.
           This is meant to use as an attachment to an email message"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if 'file_ids' in kwargs.keys():
            return True
        return False

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        if 'file_ids' in kwargs.keys():

            doc_info = StudyService().get_documents_status(study_id)
            if 'filename' in kwargs.keys():
                zip_filename = kwargs['filename']
            else:
                zip_filename = 'attachments.zip'

            # Delete the temporary zipfile if it already exist
            if os.path.exists(zip_filename):
                os.remove(zip_filename)

            file_ids = kwargs['file_ids']
            files = session.query(FileModel).filter(FileModel.id.in_(file_ids)).all()
            if files:
                # Create a temporary zipfile with the requested files
                with zipfile.ZipFile(zip_filename, mode='x', compression=zipfile.ZIP_DEFLATED) as zfw:
                    for file in files:
                        zip_key_words = doc_info[file.irb_doc_code]['zip_key_words']
                        file_name = f'{study_id} {zip_key_words} {file.name}'
                        file_data = session.query(FileDataModel).filter(FileDataModel.file_model_id == file.id).first()
                        zfw.writestr(file_name, file_data.data)

                # Add the zipfile to the DB, and grab the file_model
                with open(zip_filename, mode='rb') as handle:
                    file_model = FileService().add_workflow_file(workflow_id, None, task.name, zip_filename, 'application/zip', handle.read())

                # Delete the temporary zipfile
                os.remove(zip_filename)

                # Return the file_model
                return file_model

        else:
            raise ApiError(code='missing_file_ids',
                           message='You must include a list of file_ids.')

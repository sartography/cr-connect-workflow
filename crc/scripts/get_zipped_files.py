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

        doc_info = StudyService().get_documents_status(study_id)
        if 'filename' in kwargs.keys():
            zip_filename = kwargs['filename']
        else:
            zip_filename = 'attachments.zip'

        if 'file_ids' in kwargs.keys():
            file_ids = kwargs['file_ids']
            files = session.query(FileModel).filter(FileModel.id.in_(file_ids)).all()
            if files:
                with zipfile.ZipFile(zip_filename, mode='x', compression=zipfile.ZIP_DEFLATED) as zfw:
                    for file in files:
                        file_doc_info = doc_info[file.irb_doc_code]
                        file_path = '/'
                        if file_doc_info['category1'] != '':
                            file_path = os.path.join(file_path, file_doc_info['category1'])
                            if file_doc_info['category2'] != '':
                                file_path = os.path.join(file_path, file_doc_info['category2'])
                                if file_doc_info['category3'] != '':
                                    file_path = os.path.join(file_path, file_doc_info['category3'])

                        file_data = session.query(FileDataModel).filter(FileDataModel.file_model_id == file.id).first()
                        zfw.writestr(os.path.join(file_path, file.name), file_data.data)

                with open(zip_filename, mode='rb') as handle:
                    file_model = FileService().add_workflow_file(workflow_id, None, zip_filename, 'application/zip', handle.read())
                os.remove(zip_filename)

        else:
            raise ApiError(code='missing_file_ids',
                           message='You must include a list of file_ids.')
        return file_model

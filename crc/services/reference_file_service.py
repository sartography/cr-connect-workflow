import datetime
import hashlib
import os

from crc import session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel
from crc.services.file_service import FileService, FileType
from crc.services.spec_file_service import SpecFileService

from uuid import UUID


class ReferenceFileService(object):

    @staticmethod
    def add_reference_file(name, content_type, binary_data):
        """Create a file with the given name, but not associated with a spec or workflow.
           Only one file with the given reference name can exist."""
        file_model = session.query(FileModel). \
            filter(FileModel.is_reference == True). \
            filter(FileModel.name == name).first()
        if not file_model:
            file_extension = FileService.get_extension(name)
            file_type = FileType[file_extension].value

            file_model = FileModel(
                name=name,
                is_reference=True,
                type=file_type,
                content_type=content_type
            )
            session.add(file_model)
            session.commit()
        else:
            raise ApiError(code='file_already_exists',
                           message=f"The reference file {name} already exists.")
        return ReferenceFileService().update_reference_file(file_model, binary_data)

    def update_reference_file(self, file_model, binary_data):
        self.write_reference_file_to_system(file_model, binary_data)
        print('update_reference_file')
        return file_model

    @staticmethod
    def get_reference_file_data(file_name):
        file_model = session.query(FileModel).filter(FileModel.name == file_name).filter(
            FileModel.is_reference == True).first()
        if file_model is not None:
            sync_file_root = SpecFileService().get_sync_file_root()
            file_path = os.path.join(sync_file_root, 'Reference', file_name)
            if os.path.exists(file_path):
                mtime = os.path.getmtime(file_path)
                with open(file_path, 'rb') as f_open:
                    reference_file_data = f_open.read()
                    size = len(reference_file_data)
                    md5_checksum = UUID(hashlib.md5(reference_file_data).hexdigest())

                    reference_file_data_model = FileDataModel(data=reference_file_data,
                                                              md5_hash=md5_checksum,
                                                              size=size,
                                                              date_created=datetime.datetime.fromtimestamp(mtime),
                                                              file_model_id=file_model.id
                                                              )
                    return reference_file_data_model
        else:
            raise ApiError("file_not_found", "There is no reference file with the name '%s'" % file_name)

    def write_reference_file_to_system(self, file_model, file_data):
        file_path = self.write_reference_file_data_to_system(file_model, file_data)
        self.write_reference_file_info_to_system(file_path, file_model)

    @staticmethod
    def write_reference_file_data_to_system(file_model, file_data):
        category_name = 'Reference'
        sync_file_root = SpecFileService.get_sync_file_root()
        file_path = os.path.join(sync_file_root,
                                 category_name,
                                 file_model.name)
        SpecFileService.write_file_data_to_system(file_path, file_data)
        return file_path

    @staticmethod
    def write_reference_file_info_to_system(file_path, file_model):
        SpecFileService.write_file_info_to_system(file_path, file_model)

    @staticmethod
    def get_reference_files():
        reference_files = session.query(FileModel). \
            filter_by(is_reference=True). \
            filter(FileModel.archived == False). \
            all()
        return reference_files

import datetime
import hashlib
import os

from crc import app, session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileModelSchema, FileDataModel
from crc.services.file_service import FileService, FileType
from crc.services.spec_file_service import SpecFileService

from uuid import UUID
from sqlalchemy.exc import IntegrityError


class ReferenceFileService(object):

    @staticmethod
    def get_reference_file_path(file_name):
        sync_file_root = SpecFileService().get_sync_file_root()
        file_path = os.path.join(sync_file_root, 'Reference', file_name)
        return file_path

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

    # TODO: need a test for this?
    def update_reference_file_info(self, old_file_model, body):
        file_data = self.get_reference_file_data(old_file_model.name)

        old_file_path = self.get_reference_file_path(old_file_model.name)
        self.delete_reference_file_data(old_file_path)
        self.delete_reference_file_info(old_file_path)

        new_file_model = FileModelSchema().load(body, session=session)
        new_file_path = self.get_reference_file_path(new_file_model.name)
        self.write_reference_file_data_to_system(new_file_path, file_data.data)
        self.write_reference_file_info_to_system(new_file_path, new_file_model)
        return new_file_model

    def get_reference_file_data(self, file_name):
        file_model = session.query(FileModel).filter(FileModel.name == file_name).filter(
            FileModel.is_reference == True).first()
        if file_model is not None:
            file_path = self.get_reference_file_path(file_model.name)
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
                raise ApiError('file_not_found',
                               f"There was no file in the location: {file_path}")
        else:
            raise ApiError("file_not_found", "There is no reference file with the name '%s'" % file_name)

    def write_reference_file_to_system(self, file_model, file_data):
        file_path = self.write_reference_file_data_to_system(file_model.name, file_data)
        self.write_reference_file_info_to_system(file_path, file_model)

    def write_reference_file_data_to_system(self, file_name, file_data):
        file_path = self.get_reference_file_path(file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f_handle:
            f_handle.write(file_data)
        # SpecFileService.write_file_data_to_system(file_path, file_data)
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

    def delete_reference_file_data(self, file_name):
        file_path = self.get_reference_file_path(file_name)
        json_file_path = f'{file_path}.json'
        os.remove(file_path)
        os.remove(json_file_path)

    @staticmethod
    def delete_reference_file_info(file_name):
        file_model = session.query(FileModel).filter(FileModel.name==file_name).first()
        try:
            session.delete(file_model)
            session.commit()
        except IntegrityError as ie:
            session.rollback()
            file_model = session.query(FileModel).filter(FileModel.name==file_name).first()
            file_model.archived = True
            session.commit()
            app.logger.info("Failed to delete file: %s, so archiving it instead. Due to %s" % (file_name, str(ie)))

    def delete_reference_file(self, file_name):
        """This should remove the record in the file table, and both files on the filesystem."""
        self.delete_reference_file_data(file_name)
        self.delete_reference_file_info(file_name)

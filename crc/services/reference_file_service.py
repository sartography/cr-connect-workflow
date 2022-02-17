import datetime
import hashlib
import os

from crc import app, session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileModelSchema, FileDataModel, FileType, File
from crc.services.file_system_service import FileSystemService

from uuid import UUID
from sqlalchemy.exc import IntegrityError


class ReferenceFileService(FileSystemService):


    @staticmethod
    def root_path():
        # fixme: allow absolute directory names (but support relative)
        dir_name = app.config['SYNC_FILE_ROOT']
        app_root = app.root_path
        return os.path.join(app_root, '..', dir_name, ReferenceFileService.REFERENCE_FILES)

    @staticmethod
    def file_path(file_name: str):
        sync_file_root = ReferenceFileService().root_path()
        file_path = os.path.join(sync_file_root, file_name)
        return file_path

    @staticmethod
    def add_reference_file(file_name: str, binary_data: bytes) -> File:
        return ReferenceFileService.update_reference_file(file_name, binary_data)

    @staticmethod
    def update_reference_file(file_name: str, binary_data: bytes) -> File:
        ReferenceFileService.assert_valid_file_name(file_name)
        file_path = ReferenceFileService.file_path(file_name)
        ReferenceFileService.write_to_file_system(file_name, binary_data)
        return ReferenceFileService.to_file_object(file_name, file_path)

    @staticmethod
    def get_data(file_name):
        file_path = ReferenceFileService.file_path(file_name)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f_handle:
                spec_file_data = f_handle.read()
            return spec_file_data
        else:
            raise ApiError('file_not_found',
                           f"There is not a reference file named '{file_name}'")

    @staticmethod
    def write_to_file_system(file_name, file_data):
        file_path = ReferenceFileService.file_path(file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f_handle:
            f_handle.write(file_data)
        return file_path

    @staticmethod
    def get_reference_files():
        return FileSystemService._get_files(ReferenceFileService.root_path())

    @staticmethod
    def get_reference_file(name: str):
        files = FileSystemService._get_files(ReferenceFileService.root_path(), file_name=name)
        if len(files) < 1:
            raise ApiError('unknown_file', f"No reference file found with the name {name}", 404)
        return FileSystemService._get_files(ReferenceFileService.root_path(), file_name=name)[0]


    @staticmethod
    def delete(file_name):
        file_path = ReferenceFileService.file_path(file_name)
        os.remove(file_path)

    @staticmethod
    def last_modified(file_name):
        return FileSystemService._last_modified(ReferenceFileService.file_path(file_name))

    @staticmethod
    def timestamp(file_name):
        return FileSystemService._timestamp(ReferenceFileService.file_path(file_name))
import datetime
import os
from typing import List

from crc import app
from crc.api.common import ApiError
from crc.models.file import FileType, CONTENT_TYPES, File
from crc.models.workflow import WorkflowSpecInfo


class FileSystemService(object):

    """ Simple Service meant for extension that provides some useful
    methods for dealing with the File system.
    """
    LIBRARY_SPECS = "Library Specs"
    STAND_ALONE_SPECS = "Stand Alone"
    MASTER_SPECIFICATION = "Master Specification"
    REFERENCE_FILES = "Reference Files"
    SPECIAL_FOLDERS = [LIBRARY_SPECS, MASTER_SPECIFICATION, REFERENCE_FILES]
    CAT_JSON_FILE = "category.json"
    WF_JSON_FILE = "workflow.json"

    @staticmethod
    def root_path():
        # fixme: allow absolute files
        dir_name = app.config['SYNC_FILE_ROOT']
        app_root = app.root_path
        return os.path.join(app_root, '..', dir_name)

    @staticmethod
    def category_path(name: str):
        return os.path.join(FileSystemService.root_path(), name)


    @staticmethod
    def workflow_path(spec: WorkflowSpecInfo):
        if spec.is_master_spec:
            return os.path.join(FileSystemService.root_path(), FileSystemService.MASTER_SPECIFICATION)
        elif spec.library:
            category_path = FileSystemService.category_path(FileSystemService.LIBRARY_SPECS)
        elif spec.standalone:
            category_path = FileSystemService.category_path(FileSystemService.STAND_ALONE_SPECS)
        else:
            category_path = FileSystemService.category_path(spec.category_id)
        return os.path.join(category_path, spec.display_name)

    def next_display_order(self, spec):
        path = self.category_path(spec.category_id)
        if os.path.exists(path):
            return len(next(os.walk(path))[1])
        else:
            return 0

    @staticmethod
    def write_file_data_to_system(file_path, file_data):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f_handle:
            f_handle.write(file_data)

    @staticmethod
    def get_extension(file_name):
        basename, file_extension = os.path.splitext(file_name)
        return file_extension.lower().strip()[1:]

    @staticmethod
    def assert_valid_file_name(file_name):
        file_extension = FileSystemService.get_extension(file_name)
        if file_extension not in FileType._member_names_:
            raise ApiError('unknown_extension',
                           'The file you provided does not have an accepted extension:' +
                           file_extension, status_code=404)

    @staticmethod
    def _last_modified(file_path: str):
        # Returns the last modified date of the given file.
        timestamp = os.path.getmtime(file_path)
        return datetime.datetime.fromtimestamp(timestamp)

    @staticmethod
    def file_type(file_name):
        extension = FileSystemService.get_extension(file_name)
        return FileType[extension]

    @staticmethod
    def _get_files(file_path: str, file_name=None) -> List[File]:
        """Returns an array of File objects at the given path, can be restricted to just one file"""
        files = []
        items = os.scandir(file_path)
        for item in items:
            if item.is_file():
                if item.name == FileSystemService.WF_JSON_FILE:
                    continue # Ignore the json files.
                if file_name is not None and item.name != file_name:
                    continue
                file = FileSystemService.to_file_object_from_dir_entry(item)
                files.append(file)
        return files

    @staticmethod
    def to_file_object(file_name: str, file_path: str) -> File:
        file_type = FileSystemService.file_type(file_name)
        content_type = CONTENT_TYPES[file_type.name]
        last_modified = FileSystemService._last_modified(file_path)
        size = os.path.getsize(file_path)
        file = File.from_file_system(file_name, file_type, content_type, last_modified, size)
        return file

    @staticmethod
    def to_file_object_from_dir_entry(item: os.DirEntry):
        extension = FileSystemService.get_extension(item.name)
        try:
            file_type = FileType[extension]
            content_type = CONTENT_TYPES[file_type.name]
        except KeyError:
            raise ApiError("invalid_type", "Invalid File Type: %s, for file $%s" % (extension, item.name))
        stats = item.stat()
        file_size = stats.st_size
        last_modified = datetime.datetime.fromtimestamp(stats.st_mtime)
        return File.from_file_system(item.name, file_type, content_type, last_modified, file_size)


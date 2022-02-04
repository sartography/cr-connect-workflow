import datetime
import os
import shutil
from typing import List

from crc import app, session
from crc.api.common import ApiError
from crc.models.file import FileType, CONTENT_TYPES, File

from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException

from lxml import etree

from crc.models.workflow import WorkflowSpecInfo
from crc.services.file_system_service import FileSystemService


class SpecFileService(FileSystemService):

    """We store spec files on the file system. This allows us to take advantage of Git for
       syncing and versioning.
        The files are stored in a directory whose path is determined by the category and spec names.
    """

    @staticmethod
    def get_files(workflow_spec: WorkflowSpecInfo, file_name=None, include_libraries=False) -> List[File]:
        """ Returns all files associated with a workflow specification """
        path = SpecFileService.workflow_path(workflow_spec)
        files = SpecFileService._get_files(path, file_name)
        if include_libraries:
            for lib_name in workflow_spec.libraries:
                lib_path = SpecFileService.library_path(lib_name)
                files.extend(SpecFileService._get_files(lib_path, file_name))
        return files

    @staticmethod
    def add_file(workflow_spec: WorkflowSpecInfo, file_name: str, binary_data: bytearray) -> File:
        # Same as update
        return SpecFileService.update_file(workflow_spec, file_name, binary_data)

    @staticmethod
    def update_file(workflow_spec: WorkflowSpecInfo, file_name: str, binary_data) -> File:
        SpecFileService.assert_valid_file_name(file_name)
        file_path = SpecFileService.file_path(workflow_spec, file_name)
        SpecFileService.write_file_data_to_system(file_path, binary_data)
        file = SpecFileService.to_file_object(file_name, file_path)
        if file_name == workflow_spec.primary_file_name:
            SpecFileService.set_primary_bpmn(workflow_spec, file_name, binary_data)
        elif workflow_spec.primary_file_name is None and file.type == FileType.bpmn:
            # If no primary process exists, make this pirmary process.
            SpecFileService.set_primary_bpmn(workflow_spec, file_name, binary_data)
        return file


    @staticmethod
    def get_data(workflow_spec: WorkflowSpecModel, file_name: str):
        file_path = SpecFileService.file_path(workflow_spec, file_name)
        if not os.path.exists(file_path):
            raise ApiError("unknown_file", f"So file found with name {file_name} in {workflow_spec.display_name}")
        with open(file_path, 'rb') as f_handle:
            spec_file_data = f_handle.read()
        return spec_file_data


    @staticmethod
    def file_path(spec: WorkflowSpecModel, file_name: str):
        return os.path.join(SpecFileService.workflow_path(spec), file_name)

    @staticmethod
    def last_modified(spec: WorkflowSpecModel, file_name: str):
        path = SpecFileService.file_path(spec, file_name)
        return FileSystemService._last_modified(path)

    @staticmethod
    def delete_file(spec, file_name):
        # Fixme: Remember to remove the lookup files when the spec file is removed.
        # lookup_files = session.query(LookupFileModel).filter_by(file_model_id=file_id).all()
        # for lf in lookup_files:
        #     session.query(LookupDataModel).filter_by(lookup_file_model_id=lf.id).delete()
        #     session.query(LookupFileModel).filter_by(id=lf.id).delete()
        file_path = SpecFileService.file_path(spec, file_name)
        os.remove(file_path)

    @staticmethod
    def delete_all_files(spec):
        dir_path = SpecFileService.workflow_path(spec)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)


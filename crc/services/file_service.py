import hashlib
import os
from uuid import UUID
from xml.etree import ElementTree

from crc import session
from crc.api.common import ApiError
from crc.models.file import FileType, FileDataModel, FileModel
from crc.models.workflow import WorkflowSpecModel
from crc.services.workflow_processor import WorkflowProcessor


class FileService(object):
    """Provides consistent management and rules for storing, retrieving and processing files."""

    @staticmethod
    def add_workflow_spec_file(workflow_spec: WorkflowSpecModel,
                               name, content_type, binary_data, primary=False, is_status=False):
        """Create a new file and associate it with a workflow spec."""
        file_model = FileModel(
            workflow_spec_id=workflow_spec.id,
            name=name,
            primary=primary,
            is_status=is_status
        )
        if primary:
            bpmn: ElementTree.Element = ElementTree.fromstring(binary_data)
            workflow_spec.primary_process_id = WorkflowProcessor.get_process_id(bpmn)
            print("Locating Process Id for " + name + "  " + workflow_spec.primary_process_id)

        return FileService.update_file(file_model, binary_data, content_type)

    @staticmethod
    def add_form_field_file(study_id, workflow_id, task_id, form_field_key, name, content_type, binary_data):
        """Create a new file and associate it with a user task form field within a workflow."""
        file_model = FileModel(
            version=0,
            study_id=study_id,
            workflow_id=workflow_id,
            task_id=task_id,
            name=name,
            form_field_key=form_field_key
        )
        return FileService.update_file(file_model, binary_data, content_type)

    @staticmethod
    def add_task_file(study_id, workflow_id, task_id, name, content_type, binary_data):
        """Create a new file and associate it with an executing task within a workflow."""
        file_model = FileModel(
            study_id=study_id,
            workflow_id=workflow_id,
            task_id=task_id,
            name=name,
        )
        return FileService.update_file(file_model, binary_data, content_type)

    @staticmethod
    def add_reference_file(name, content_type, binary_data):
        """Create a file with the given name, but not associated with a spec or workflow.
           Only one file with the given reference name can exist."""
        file_model = session.query(FileModel). \
            filter(FileModel.is_reference == True). \
            filter(FileModel.name == name).first()
        if not file_model:
            file_model = FileModel(
                name=name,
                is_reference=True
            )
        return FileService.update_file(file_model, binary_data, content_type)

    @staticmethod
    def get_extension(file_name):
        basename, file_extension = os.path.splitext(file_name)
        return file_extension.lower().strip()[1:]

    @staticmethod
    def update_file(file_model, binary_data, content_type):

        file_data_model = session.query(FileDataModel). \
            filter_by(file_model_id=file_model.id,
                      version=file_model.latest_version
                      ).with_for_update().first()
        md5_checksum = UUID(hashlib.md5(binary_data).hexdigest())
        if (file_data_model is not None and md5_checksum == file_data_model.md5_hash):
            # This file does not need to be updated, it's the same file.
            return file_model

        # Verify the extension
        file_extension = FileService.get_extension(file_model.name)
        if file_extension not in FileType._member_names_:
            raise ApiError('unknown_extension',
                           'The file you provided does not have an accepted extension:' +
                           file_extension, status_code=404)
        else:
            file_model.type = FileType[file_extension]
            file_model.content_type = content_type

        if file_data_model is None:
            version = 1
        else:
            version = file_data_model.version + 1

        file_model.latest_version = version
        file_data_model = FileDataModel(data=binary_data, file_model=file_model, version=version,
                                        md5_hash=md5_checksum)

        session.add_all([file_model, file_data_model])
        session.commit()
        session.flush()  # Assure the id is set on the model before returning it.
        return file_model

    @staticmethod
    def get_files(workflow_spec_id=None,
                  study_id=None, workflow_id=None, task_id=None, form_field_key=None,
                  name=None, is_reference=False):
        query = session.query(FileModel).filter_by(is_reference=is_reference)
        if workflow_spec_id:
            query = query.filter_by(workflow_spec_id=workflow_spec_id)
        if study_id:
            query = query.filter_by(study_id=study_id)
        if workflow_id:
            query = query.filter_by(workflow_id=workflow_id)
        if task_id:
            query = query.filter_by(task_id=str(task_id))
        if form_field_key:
            query = query.filter_by(form_field_key=form_field_key)
        if name:
            query = query.filter_by(name=form_field_key)

        results = query.all()
        return results

    @staticmethod
    def get_file_data(file_id, file_model=None):
        """Returns the file_data that is associated with the file model id, if an actual file_model
        is provided, uses that rather than looking it up again."""
        if file_model is None:
            file_model = session.query(FileModel).filter(FileModel.id == file_id).first()
        return session.query(FileDataModel) \
            .filter(FileDataModel.file_model_id == file_id) \
            .filter(FileDataModel.version == file_model.latest_version) \
            .first()

    @staticmethod
    def get_reference_file_data(file_name):
        file_model = session.query(FileModel). \
            filter(FileModel.is_reference == True). \
            filter(FileModel.name == file_name).first()
        if not file_model:
            raise ApiError("file_not_found", "There is no reference file with the name '%s'" % file_name)
        return FileService.get_file_data(file_model.id, file_model)

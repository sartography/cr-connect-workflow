import os
from datetime import datetime

from crc import session
from crc.api.common import ApiErrorSchema, ApiError
from crc.models.file import FileType, FileDataModel, FileModelSchema, FileModel


class FileService(object):
    """Provides consistent management and rules for storing, retrieving and processing files."""

    DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @staticmethod
    def add_workflow_spec_file(workflow_spec_id, name, content_type, binary_data):
        """Create a new file and associate it with a workflow spec."""
        file_model = FileModel(
            version=0,
            workflow_spec_id=workflow_spec_id,
            name=name,
        )
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
            version=0,
            study_id=study_id,
            workflow_id=workflow_id,
            task_id=task_id,
            name=name,
        )
        return FileService.update_file(file_model, binary_data, content_type)

    @staticmethod
    def update_file(file_model, binary_data, content_type):

        file_model.version = file_model.version + 1
        file_model.last_updated = datetime.now()
        file_model.content_type = content_type

        # Verify the extension
        basename, file_extension = os.path.splitext(file_model.name)
        file_extension = file_extension.lower().strip()[1:]
        if file_extension not in FileType._member_names_:
            return ApiErrorSchema().dump(ApiError('unknown_extension',
                                                  'The file you provided does not have an accepted extension:' +
                                                  file_extension)), 404
        else:
            file_model.type = FileType[file_extension]

        file_data_model = session.query(FileDataModel).filter_by(file_model_id=file_model.id).with_for_update().first()
        if file_data_model is None:
            file_data_model = FileDataModel(data=binary_data, file_model=file_model)
        else:
            file_data_model.data = binary_data

        session.add_all([file_model, file_data_model])
        session.commit()
        session.flush()  # Assure the id is set on the model before returning it.
        return file_model

    @staticmethod
    def get_files(workflow_spec_id=None, study_id=None, workflow_id=None, task_id=None, form_field_key=None):
        query = session.query(FileModel)
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

        results = query.all()
        return results

    @staticmethod
    def get_file_data(file_id):
        """Returns the file_data that is associated with the file model id"""
        return session.query(FileDataModel).filter(FileDataModel.file_model_id == file_id).first()

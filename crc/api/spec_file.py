from crc import session
from flask_bpmn.api.common import ApiError
from crc.models.file import FileSchema, FileType
from crc.services.spec_file_service import SpecFileService

from flask import send_file

import io
import connexion

from crc.services.workflow_spec_service import WorkflowSpecService

def get_files(spec_id, include_libraries=False):
    if spec_id is None:
        raise ApiError(code='missing_spec_id',
                       message='Please specify the workflow_spec_id.')
    workflow_spec_service = WorkflowSpecService()
    workflow_spec = workflow_spec_service.get_spec(spec_id)
    if workflow_spec is None:
        raise ApiError(code='unknown_spec',
                       message=f'Unknown Spec: {spec_id}')
    files = SpecFileService.get_files(workflow_spec,
                                      include_libraries=include_libraries)
    return FileSchema(many=True).dump(files)


def get_file(spec_id, file_name):
    workflow_spec_service = WorkflowSpecService()
    workflow_spec = workflow_spec_service.get_spec(spec_id)
    files = SpecFileService.get_files(workflow_spec, file_name)
    if len(files) == 0:
        raise ApiError(code='unknown file',
                       message=f'No information exists for file {file_name}'
                               f' it does not exist in workflow {spec_id}.', status_code=404)
    return FileSchema().dump(files[0])


def add_file(spec_id):
    workflow_spec_service = WorkflowSpecService()
    workflow_spec = workflow_spec_service.get_spec(spec_id)
    file = connexion.request.files['file']
    file = SpecFileService.add_file(workflow_spec, file.filename, file.stream.read())
    if not workflow_spec.primary_process_id and file.type == FileType.bpmn.value:
        SpecFileService.set_primary_bpmn(workflow_spec, file.name)
        workflow_spec_service.update_spec(workflow_spec)
    return FileSchema().dump(file)


def update(spec_id, file_name, is_primary):
    workflow_spec_service = WorkflowSpecService()
    workflow_spec = workflow_spec_service.get_spec(spec_id)
    files = SpecFileService.get_files(workflow_spec, file_name)
    if len(files) < 1:
        raise ApiError(code='unknown file',
                       message=f'No information exists for file {file_name}'
                               f' it does not exist in workflow {spec_id}.')
    file = files[0]
    if is_primary:
        SpecFileService.set_primary_bpmn(workflow_spec, file_name)
        workflow_spec_service.update_spec(workflow_spec)
    return FileSchema().dump(file)


def update_data(spec_id, file_name):
    workflow_spec_service = WorkflowSpecService()
    workflow_spec_model = workflow_spec_service.get_spec(spec_id)
    if workflow_spec_model is None:
        raise ApiError(code='missing_spec',
                       message=f'The workflow spec for id {spec_id} does not exist.')
    file_data = connexion.request.files['file']
    file = SpecFileService.update_file(workflow_spec_model, file_name, file_data.stream.read())
    return FileSchema().dump(file)


def get_data(spec_id, file_name):
    workflow_spec_service = WorkflowSpecService()
    workflow_spec = workflow_spec_service.get_spec(spec_id)
    file_data = SpecFileService.get_data(workflow_spec, file_name)
    if file_data is not None:
        file_info = SpecFileService.get_files(workflow_spec, file_name)[0]
        return send_file(
            io.BytesIO(file_data),
            attachment_filename=file_name,
            mimetype=file_info.content_type,
            cache_timeout=-1  # Don't cache these files on the browser.
        )
    else:
        raise ApiError(code='missing_data_model',
                       message=f'The data model for file {file_name}'
                               f' does not exist in workflow {spec_id}.')


def delete(spec_id, file_name):
    workflow_spec_service = WorkflowSpecService()
    workflow_spec = workflow_spec_service.get_spec(spec_id)
    SpecFileService.delete_file(workflow_spec, file_name)

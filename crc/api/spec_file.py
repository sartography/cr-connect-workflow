from crc import session
from crc.api.common import ApiError
from crc.api.file import to_file_api, get_file_info
from crc.models.file import FileModel, FileSchema, FileType
from crc.models.workflow import WorkflowSpecModel
from crc.services.spec_file_service import SpecFileService

from flask import send_file

import io
import connexion


def get_spec_files(workflow_spec_id, include_libraries=False):
    if workflow_spec_id is None:
        raise ApiError(code='missing_spec_id',
                       message='Please specify the workflow_spec_id.')
    file_models = SpecFileService.get_spec_files(workflow_spec_id=workflow_spec_id,
                                                 include_libraries=include_libraries)
    files = [to_file_api(model) for model in file_models]
    return FileSchema(many=True).dump(files)


def add_spec_file(workflow_spec_id):
    if workflow_spec_id:
        file = connexion.request.files['file']
        # check if we have a primary already
        have_primary = FileModel.query.filter(FileModel.workflow_spec_id==workflow_spec_id, FileModel.type==FileType.bpmn, FileModel.primary==True).all()
        # set this to primary if we don't already have one
        if not have_primary:
            primary = True
        else:
            primary = False
        workflow_spec = session.query(WorkflowSpecModel).filter_by(id=workflow_spec_id).first()
        file_model = SpecFileService.add_workflow_spec_file(workflow_spec, file.filename, file.content_type,
                                                            file.stream.read(), primary=primary)
        return FileSchema().dump(to_file_api(file_model))
    else:
        raise ApiError(code='missing_workflow_spec_id',
                       message="You must include a workflow_spec_id")


def update_spec_file_data(file_id):
    file_model = session.query(FileModel).filter_by(id=file_id).with_for_update().first()
    if file_model is None:
        raise ApiError('no_such_file', f'The file id you provided ({file_id}) does not exist')
    if file_model.workflow_spec_id is None:
        raise ApiError(code='no_spec_id',
                       message=f'There is no workflow_spec_id for file {file_id}.')
    workflow_spec_model = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id==file_model.workflow_spec_id).first()
    if workflow_spec_model is None:
        raise ApiError(code='missing_spec',
                       message=f'The workflow spec for id {file_model.workflow_spec_id} does not exist.')

    file = connexion.request.files['file']
    SpecFileService().update_spec_file_data(workflow_spec_model, file_model.name, file.stream.read())
    return FileSchema().dump(to_file_api(file_model))


def get_spec_file_data(file_id):
    file_model = session.query(FileModel).filter(FileModel.id==file_id).first()
    if file_model is not None:
        file_data_model = SpecFileService().get_spec_file_data(file_id)
        if file_data_model is not None:
            return send_file(
                io.BytesIO(file_data_model.data),
                attachment_filename=file_model.name,
                mimetype=file_model.content_type,
                cache_timeout=-1  # Don't cache these files on the browser.
            )
        else:
            raise ApiError(code='missing_data_model',
                           message=f'The data model for file {file_id} does not exist.')
    else:
        raise ApiError(code='missing_file_model',
                       message=f'The file model for file_id {file_id} does not exist.')


def get_spec_file_info(file_id):
    return get_file_info(file_id)


def update_spec_file_info(file_id, body):
    if file_id is None:
        raise ApiError('no_such_file', 'Please provide a valid File ID.')
    file_model = session.query(FileModel).filter(FileModel.id==file_id).first()
    if file_model is None:
        raise ApiError('unknown_file_model', 'The file_model "' + file_id + '" is not recognized.')

    new_file_model = SpecFileService().update_spec_file_info(file_model, body)
    return FileSchema().dump(to_file_api(new_file_model))


def delete_spec_file(file_id):
    SpecFileService.delete_spec_file(file_id)



import io
import os
from datetime import datetime

import connexion
from flask import send_file

from crc import session
from crc.api.common import ApiError
from crc.api.user import verify_token
from crc.models.file import FileSchema, FileModel, File, FileModelSchema, FileDataModel, FileType, CONTENT_TYPES
from crc.models.workflow import WorkflowSpecModel
from crc.services.document_service import DocumentService
from crc.services.file_service import FileService
from crc.services.reference_file_service import ReferenceFileService
from crc.services.spec_file_service import SpecFileService


def to_file_api(file_model):
    """Converts a FileModel object to something we can return via the api"""
    if file_model.workflow_spec_id is not None:
        file_data_model = SpecFileService().get_spec_file_data(file_model.id)
    elif file_model.is_reference:
        file_data_model = ReferenceFileService().get_reference_file_data(file_model.name)
    else:
        file_data_model = FileService.get_file_data(file_model.id)
    return File.from_models(file_model, file_data_model,
                            DocumentService.get_dictionary())


def get_files(workflow_id=None, form_field_key=None,study_id=None):
    if workflow_id is None:
        raise ApiError('missing_parameter',
                       'Please specify a workflow_id with an optional form_field_key')

    if study_id is not None:
        file_models = FileService.get_files_for_study(study_id=study_id, irb_doc_code=form_field_key)
    else:
        file_models = FileService.get_files(workflow_id=workflow_id,
                                            irb_doc_code=form_field_key)

    files = (to_file_api(model) for model in file_models)
    return FileSchema(many=True).dump(files)


def get_spec_files(workflow_spec_id, include_libraries=False):
    if workflow_spec_id is None:
        raise ApiError(code='missing_spec_id',
                       message='Please specify the workflow_spec_id.')
    file_models = SpecFileService.get_spec_files(workflow_spec_id=workflow_spec_id,
                                                 include_libraries=include_libraries)
    files = [to_file_api(model) for model in file_models]
    return FileSchema(many=True).dump(files)


def get_reference_files():
    """Gets a list of all reference files"""
    results = ReferenceFileService.get_reference_files()
    files = (to_file_api(model) for model in results)
    return FileSchema(many=True).dump(files)


def add_file(workflow_id=None, task_spec_name=None, form_field_key=None):
    file = connexion.request.files['file']
    if workflow_id:
        if form_field_key is None:
            raise ApiError('invalid_workflow_file',
                           'When adding a workflow related file, you must specify a form_field_key')
        if task_spec_name is None:
            raise ApiError('invalid_workflow_file',
                           'When adding a workflow related file, you must specify a task_spec_name')
        file_model = FileService.add_workflow_file(workflow_id=workflow_id, irb_doc_code=form_field_key,
                                                   task_spec_name=task_spec_name,
                                                   name=file.filename, content_type=file.content_type,
                                                   binary_data=file.stream.read())
    else:
        raise ApiError("invalid_file", "You must supply either a workflow spec id or a workflow_id and form_field_key.")

    return FileSchema().dump(to_file_api(file_model))


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


def get_reference_file_data(name):
    file_extension = FileService.get_extension(name)
    content_type = CONTENT_TYPES[file_extension]
    file_data = ReferenceFileService().get_reference_file_data(name)
    return send_file(
        io.BytesIO(file_data.data),
        attachment_filename=name,
        mimetype=content_type,
        cache_timeout=-1  # Don't cache these files on the browser.
    )


def get_reference_file_info(name):
    """Return metadata for a reference file"""
    file_model = session.query(FileModel).\
        filter_by(name=name).with_for_update().\
        filter_by(archived=False).with_for_update().\
        first()
    if file_model is None:
        # TODO: Should this be 204 or 404?
        raise ApiError('no_such_file', f'The reference file name you provided ({name}) does not exist', status_code=404)
    return FileSchema().dump(to_file_api(file_model))


def update_reference_file_data(name):
    """Uses the file service to manage reference-files. They will be used in script tasks to compute values."""
    if 'file' not in connexion.request.files:
        raise ApiError('invalid_file',
                       'Expected a file named "file" in the multipart form request', status_code=400)

    file = connexion.request.files['file']

    name_extension = FileService.get_extension(name)
    file_extension = FileService.get_extension(file.filename)
    if name_extension != file_extension:
        raise ApiError('invalid_file_type',
                       "The file you uploaded has an extension '%s', but it should have an extension of '%s' " %
                       (file_extension, name_extension))

    file_model = session.query(FileModel).filter(FileModel.name==name).first()
    if not file_model:
        raise ApiError(code='file_does_not_exist',
                       message=f"The reference file {name} does not exist.")
    else:
        ReferenceFileService().update_reference_file(file_model, file.stream.read())

    return FileSchema().dump(to_file_api(file_model))


# TODO: need a test for this
def update_reference_file_info(name, body):
    if name is None:
        raise ApiError(code='missing_parameter',
                       message='Please provide a reference file name')
    file_model = session.query(FileModel).filter(FileModel.name==name).first()
    if file_model is None:
        raise ApiError(code='no_such_file',
                       message=f"No reference file was found with name: {name}")
    new_file_model = ReferenceFileService.update_reference_file_info(file_model, body)
    return FileSchema().dump(to_file_api(new_file_model))


def add_reference_file():
    file = connexion.request.files['file']
    file_model = ReferenceFileService.add_reference_file(name=file.filename,
                                                    content_type=file.content_type,
                                                    binary_data=file.stream.read())
    return FileSchema().dump(to_file_api(file_model))


def update_file_data(file_id):
    file_model = session.query(FileModel).filter_by(id=file_id).with_for_update().first()
    file = connexion.request.files['file']
    if file_model is None:
        raise ApiError('no_such_file', f'The file id you provided ({file_id}) does not exist')
    file_model = FileService.update_file(file_model, file.stream.read(), file.content_type)
    return FileSchema().dump(to_file_api(file_model))


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


def get_file_data_by_hash(md5_hash):
    filedatamodel = session.query(FileDataModel).filter(FileDataModel.md5_hash == md5_hash).first()
    return get_file_data(filedatamodel.file_model_id, version=filedatamodel.version)


def get_file_data(file_id, version=None):
    file_model = session.query(FileModel).filter(FileModel.id==file_id).first()
    if file_model is not None:
        file_data_model = FileService.get_file_data(file_id, version)
        if file_data_model is not None:
            return send_file(
                io.BytesIO(file_data_model.data),
                attachment_filename=file_model.name,
                mimetype=file_model.content_type,
                cache_timeout=-1  # Don't cache these files on the browser.
            )
        else:
            raise ApiError('missing_data_model', f'The data model for file ({file_id}) does not exist')
    else:
        raise ApiError('missing_file_model', f'The file id you provided ({file_id}) does not exist')


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


def get_file_data_link(file_id, auth_token, version=None):
    if not verify_token(auth_token):
        raise ApiError('not_authenticated', 'You need to include an authorization token in the URL with this')
    file_model = session.query(FileModel).filter(FileModel.id==file_id).first()
    if file_model.workflow_spec_id is not None:
        file_data = SpecFileService().get_spec_file_data(file_id)
    elif file_model.is_reference:
        file_data = ReferenceFileService().get_reference_file_data(file_id)
    else:
        file_data = FileService.get_file_data(file_id, version)
    if file_data is None:
        raise ApiError('no_such_file', f'The file id you provided ({file_id}) does not exist')
    return send_file(
        io.BytesIO(file_data.data),
        attachment_filename=file_model.name,
        mimetype=file_model.content_type,
        cache_timeout=-1,  # Don't cache these files on the browser.
        last_modified=file_data.date_created,
        as_attachment=True
    )


def get_file_info(file_id):
    file_model = session.query(FileModel).filter_by(id=file_id).with_for_update().first()
    if file_model is None:
        raise ApiError('no_such_file', f'The file id you provided ({file_id}) does not exist', status_code=404)
    return FileSchema().dump(to_file_api(file_model))


def get_spec_file_info(file_id):
    return get_file_info(file_id)


def update_file_info(file_id, body):
    if file_id is None:
        raise ApiError('no_such_file', 'Please provide a valid File ID.')

    file_model = session.query(FileModel).filter_by(id=file_id).first()

    if file_model is None:
        raise ApiError('unknown_file_model', 'The file_model "' + file_id + '" is not recognized.')

    file_model = FileModelSchema().load(body, session=session)
    session.add(file_model)
    session.commit()
    return FileSchema().dump(to_file_api(file_model))


def update_spec_file_info(file_id, body):
    if file_id is None:
        raise ApiError('no_such_file', 'Please provide a valid File ID.')
    file_model = session.query(FileModel).filter(FileModel.id==file_id).first()
    if file_model is None:
        raise ApiError('unknown_file_model', 'The file_model "' + file_id + '" is not recognized.')

    new_file_model = SpecFileService().update_spec_file_info(file_model, body)
    return FileSchema().dump(to_file_api(new_file_model))


def delete_file(file_id):
    FileService.delete_file(file_id)


def delete_spec_file(file_id):
    SpecFileService.delete_spec_file(file_id)


def delete_reference_file(name):
    ReferenceFileService().delete_reference_file(name)


def dmn_from_ss():
    file = connexion.request.files['file']
    result = FileService.dmn_from_spreadsheet(file)
    return send_file(
        io.BytesIO(result),
        attachment_filename='temp_dmn.dmn',
        mimetype='text/xml',
        cache_timeout=-1,  # Don't cache these files on the browser.
        last_modified=datetime.now()
    )

import io
import os
from datetime import datetime

import connexion
from flask import send_file

from crc import session
from crc.api.common import ApiErrorSchema, ApiError
from crc.models.file import FileModelSchema, FileModel, FileDataModel, FileType
from crc.services.file_service import FileService


def get_files(workflow_spec_id=None, study_id=None, workflow_id=None, task_id=None, form_field_key=None):
    if all(v is None for v in [workflow_spec_id, study_id, workflow_id, task_id, form_field_key]):
        return ApiErrorSchema().dump(ApiError('missing_parameter',
                                              'Please specify at least one of workflow_spec_id, study_id, '
                                              'workflow_id, and task_id for this file in the HTTP parameters')), 400

    results = FileService.get_files(workflow_spec_id, study_id, workflow_id, task_id, form_field_key)
    return FileModelSchema(many=True).dump(results)


def add_file(workflow_spec_id=None, study_id=None, workflow_id=None, task_id=None, form_field_key=None):
    all_none = all(v is None for v in [workflow_spec_id, study_id, workflow_id, task_id, form_field_key])
    missing_some = (workflow_spec_id is None) and (None in [study_id, workflow_id, task_id, form_field_key])
    if all_none or missing_some:
        return ApiErrorSchema().dump(ApiError('missing_parameter',
                                              'Please specify either a workflow_spec_id or all 3 of study_id, '
                                              'workflow_id, and task_id for this file in the HTTP parameters')), 404
    if 'file' not in connexion.request.files:
        return ApiErrorSchema().dump(ApiError('invalid_file',
                                              'Expected a file named "file" in the multipart form request')), 404

    file = connexion.request.files['file']
    if workflow_spec_id:
        file_model = FileService.add_workflow_spec_file(workflow_spec_id, file.filename, file.content_type, file.stream.read())
    else:
        file_model = FileService.add_form_field_file(study_id, workflow_id, task_id, form_field_key, file.filename, file.content_type, file.stream.read())

    return FileModelSchema().dump(file_model)


def update_file_data(file_id):
    file_model = session.query(FileModel).filter_by(id=file_id).with_for_update().first()
    file = connexion.request.files['file']
    if file_model is None:
        return ApiErrorSchema().dump(ApiError('no_such_file', 'The file id you provided does not exist')), 404
    file_model = FileService.update_file(file_model, file.stream.read(), file.content_type)
    return FileModelSchema().dump(file_model)


def get_file_data(file_id):
    file_data = FileService.get_file_data(file_id)
    if file_data is None:
        return ApiErrorSchema().dump(ApiError('no_such_file', 'The file id you provided does not exist')), 404
    return send_file(
        io.BytesIO(file_data.data),
        attachment_filename=file_data.file_model.name,
        mimetype=file_data.file_model.content_type,
        cache_timeout=-1  # Don't cache these files on the browser.
    )


def get_file_info(file_id):
    file_model = session.query(FileModel).filter_by(id=file_id).with_for_update().first()
    if file_model is None:
        return ApiErrorSchema().dump(ApiError('no_such_file', 'The file id you provided does not exist')), 404
    return FileModelSchema().dump(file_model)


def update_file_info(file_id, body):
    if file_id is None:
        error = ApiError('unknown_file', 'Please provide a valid File ID.')
        return ApiErrorSchema.dump(error), 404

    file_model = session.query(FileModel).filter_by(id=file_id).first()

    if file_model is None:
        error = ApiError('unknown_file_model', 'The file_model "' + file_id + '" is not recognized.')
        return ApiErrorSchema.dump(error), 404

    file_model = FileModelSchema().load(body, session=session)
    session.add(file_model)
    session.commit()
    return FileModelSchema().dump(file_model)


def delete_file(file_id):
    session.query(FileDataModel).filter_by(file_model_id=file_id).delete()
    session.query(FileModel).filter_by(id=file_id).delete()
    session.commit()

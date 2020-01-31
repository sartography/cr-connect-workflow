import io
import os
from datetime import datetime

import connexion
from flask import send_file

from crc import session
from crc.api.common import ApiErrorSchema, ApiError
from crc.models.file import FileModelSchema, FileModel, FileDataModel, FileType


def update_file_from_request(file_model):
    if 'file' not in connexion.request.files:
        return ApiErrorSchema().dump(ApiError('invalid_file',
                                              'Expected a file named "file" in the multipart form request')), 404
    file = connexion.request.files['file']
    file_model.name = file.filename
    file_model.version = file_model.version + 1
    file_model.last_updated = datetime.now()
    file_model.content_type = file.content_type

    # Verify the extension
    basename, file_extension = os.path.splitext(file.filename)
    file_extension = file_extension.lower().strip()[1:]
    if file_extension not in FileType._member_names_:
        return ApiErrorSchema().dump(ApiError('unknown_extension',
                                              'The file you provided does not have an accepted extension:' +
                                              file_extension)), 404
    else:
        file_model.type = FileType[file_extension]

    file_data_model = session.query(FileDataModel).filter_by(id=file_model.id).with_for_update().first()
    if file_data_model is None:
        file_data_model = FileDataModel(data=file.stream.read(), file_model=file_model)
    else:
        file_data_model.data = file.stream.read()

    session.add(file_data_model)
    session.add(file_model)
    session.commit()
    session.flush()  # Assure the id is set on the model before returning it.


def get_files(spec_id):
    if spec_id:
        schema = FileModelSchema(many=True)
        return schema.dump(session.query(FileModel).filter_by(workflow_spec_id=spec_id).all())
    else:
        error = ApiError('no_files_found', 'Please provide some parameters so we can find the files you need.')
        return ApiErrorSchema().dump(error), 400


def add_file():
    if 'workflow_spec_id' not in connexion.request.form:
        return ApiErrorSchema().dump(ApiError('missing_spec_id',
                                              'Please specify a workflow_spec_id for this file in the form')), 404
    file_model = FileModel(version=0, workflow_spec_id=connexion.request.form['workflow_spec_id'])
    update_file_from_request(file_model)
    return FileModelSchema().dump(file_model)


def update_file_data(file_id):
    file_model = session.query(FileModel).filter_by(id=file_id).with_for_update().first()
    if file_model is None:
        return ApiErrorSchema().dump(ApiError('no_such_file', 'The file id you provided does not exist')), 404
    update_file_from_request(file_model)
    return FileModelSchema().dump(file_model)


def get_file_data(file_id):
    file_data = session.query(FileDataModel).filter_by(id=file_id).first()
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

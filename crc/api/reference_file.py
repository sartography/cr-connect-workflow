from crc import session
from crc.api.common import ApiError
from crc.api.file import to_file_api
from crc.models.file import FileModel, FileSchema, CONTENT_TYPES
from crc.services.file_service import FileService
from crc.services.reference_file_service import ReferenceFileService

from flask import send_file

import io
import connexion


def get_reference_files():
    """Gets a list of all reference files"""
    results = ReferenceFileService.get_reference_files()
    files = (to_file_api(model) for model in results)
    return FileSchema(many=True).dump(files)


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


# TODO: do we need a test for this?
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


def delete_reference_file(name):
    ReferenceFileService().delete_reference_file(name)



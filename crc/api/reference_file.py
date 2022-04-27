from crc.api.common import ApiError
from crc.models.file import FileSchema, CONTENT_TYPES
from crc.services.reference_file_service import ReferenceFileService

from flask import send_file

import io
import connexion


def get_reference_files():
    """Gets a list of all reference files"""
    files = ReferenceFileService.get_reference_files()
    return FileSchema(many=True).dump(files)


def get_reference_file_data(name):
    file_extension = ReferenceFileService.get_extension(name)
    content_type = CONTENT_TYPES[file_extension]
    file_data = ReferenceFileService().get_data(name)
    return send_file(
        io.BytesIO(file_data),
        attachment_filename=name,
        mimetype=content_type,
        cache_timeout=-1  # Don't cache these files on the browser.
    )


def get_reference_file_info(name):
    """Return metadata for a reference file"""
    return FileSchema().dump(ReferenceFileService.get_reference_file(name))


def update_reference_file_data(name):
    """Uses the file service to manage reference-files. They will be used in script tasks to compute values."""
    if 'file' not in connexion.request.files:
        raise ApiError('invalid_file',
                       'Expected a file named "file" in the multipart form request', status_code=400)

    file = connexion.request.files['file']
    name_extension = ReferenceFileService.get_extension(name)
    file_extension = ReferenceFileService.get_extension(file.filename)
    if name_extension != file_extension:
        raise ApiError('invalid_file_type',
                       "The file you uploaded has an extension '%s', but it should have an extension of '%s' " %
                       (file_extension, name_extension))

    return_file = ReferenceFileService.update_reference_file(file_name=name, binary_data=file.stream.read())
    return FileSchema().dump(return_file)


def add_reference_file():
    file = connexion.request.files['file']
    file_model = ReferenceFileService.add_reference_file(file.filename, file.stream.read())
    return FileSchema().dump(file_model)


def delete_reference_file(name):
    ReferenceFileService().delete(name)



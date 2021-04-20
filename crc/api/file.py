import io
from typing import List

import connexion
from flask import send_file

from crc import session
from crc.api.common import ApiError
from crc.models.file import FileSchema, FileModel, File, FileModelSchema, FileDataModel
from crc.models.api_models import DocumentDirectory, DocumentDirectorySchema
from crc.models.workflow import WorkflowSpecModel
from crc.services.file_service import FileService

def ensure_exists(output,categories,expanded):
    """
    This is a recursive function, it expects a list of
    levels with a file object at the end (kinda like duck,duck,duck,goose)

    for each level, it makes sure that level is already in the structure and if it is not
    it will add it

    function terminates upon getting an entry that is a file object ( or really anything but string)
    """
    currentitem = categories[0]
    found = False
    if isinstance(currentitem,str):
        for item in output:
            if item.level == currentitem:
                found = True
                item.filecount = item.filecount + 1
                item.expanded = expanded
                ensure_exists(item.children,categories[1:],expanded)
        if not found:
            newlevel = DocumentDirectory(level=currentitem)
            newlevel.filecount = 1
            newlevel.expanded = expanded
            output.append(newlevel)
            ensure_exists(newlevel.children,categories[1:],expanded)
    else:
        newlevel = DocumentDirectory(file=currentitem)
        newlevel.expanded = expanded
        output.append(newlevel)


def get_document_directory(study_id,workflow_id=None):
    """
    return a nested list of files arranged according to the category hirearchy
    defined in the doc dictionary
    """
    output = []
    doc_dict = FileService.get_doc_dictionary()
    file_models = FileService.get_files_for_study(study_id=study_id)
    files = (to_file_api(model) for model in file_models)
    for file in files:
        doc_code = doc_dict[file.irb_doc_code]
        if workflow_id:
            expand = file.workflow_id == int(workflow_id)
        else:
            expand = False
        print(expand)
        categories = [x for x in [doc_code['category1'],doc_code['category2'],doc_code['category3'],file] if x != '']
        ensure_exists(output,categories,expanded=expand)
    return DocumentDirectorySchema(many=True).dump(output)


def to_file_api(file_model):
    """Converts a FileModel object to something we can return via the api"""
    return File.from_models(file_model, FileService.get_file_data(file_model.id),
                            FileService.get_doc_dictionary())


def get_files(workflow_spec_id=None, workflow_id=None, form_field_key=None,study_id=None):
    if all(v is None for v in [workflow_spec_id, workflow_id, form_field_key,study_id]):
        raise ApiError('missing_parameter',
                       'Please specify either a workflow_spec_id or a '
                       'workflow_id with an optional form_field_key')

    if study_id is not None:
        file_models = FileService.get_files_for_study(study_id=study_id)
    else:
        file_models = FileService.get_files(workflow_spec_id=workflow_spec_id,
                                        workflow_id=workflow_id,
                                        irb_doc_code=form_field_key)

    files = (to_file_api(model) for model in file_models)
    return FileSchema(many=True).dump(files)


def get_reference_files():
    results = FileService.get_files(is_reference=True)
    files = (to_file_api(model) for model in results)
    return FileSchema(many=True).dump(files)


def add_file(workflow_spec_id=None, workflow_id=None, form_field_key=None):
    file = connexion.request.files['file']
    if workflow_id:
        if form_field_key is None:
            raise ApiError('invalid_workflow_file',
                           'When adding a workflow related file, you must specify a form_field_key')
        file_model = FileService.add_workflow_file(workflow_id=workflow_id, irb_doc_code=form_field_key,
                                                   name=file.filename, content_type=file.content_type,
                                                   binary_data=file.stream.read())
    elif workflow_spec_id:
        workflow_spec = session.query(WorkflowSpecModel).filter_by(id=workflow_spec_id).first()
        file_model = FileService.add_workflow_spec_file(workflow_spec, file.filename, file.content_type,
                                                        file.stream.read())
    else:
        raise ApiError("invalid_file", "You must supply either a workflow spec id or a workflow_id and form_field_key.")

    return FileSchema().dump(to_file_api(file_model))


def get_reference_file(name):
    file_data = FileService.get_reference_file_data(name)
    return send_file(
        io.BytesIO(file_data.data),
        attachment_filename=file_data.file_model.name,
        mimetype=file_data.file_model.content_type,
        cache_timeout=-1  # Don't cache these files on the browser.
    )


def set_reference_file(name):
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

    file_models = FileService.get_files(name=name, is_reference=True)
    if len(file_models) == 0:
        file_model = FileService.add_reference_file(name, file.content_type, file.stream.read())
    else:
        file_model = file_models[0]
        FileService.update_file(file_models[0], file.stream.read(), file.content_type)

    return FileSchema().dump(to_file_api(file_model))


def update_file_data(file_id):
    file_model = session.query(FileModel).filter_by(id=file_id).with_for_update().first()
    file = connexion.request.files['file']
    if file_model is None:
        raise ApiError('no_such_file', 'The file id you provided does not exist')
    file_model = FileService.update_file(file_model, file.stream.read(), file.content_type)
    return FileSchema().dump(to_file_api(file_model))

def get_file_data_by_hash(md5_hash):
    filedatamodel = session.query(FileDataModel).filter(FileDataModel.md5_hash == md5_hash).first()
    return get_file_data(filedatamodel.file_model_id,version=filedatamodel.version)

def get_file_data(file_id, version=None):
    file_data = FileService.get_file_data(file_id, version)
    if file_data is None:
        raise ApiError('no_such_file', 'The file id you provided does not exist')
    return send_file(
        io.BytesIO(file_data.data),
        attachment_filename=file_data.file_model.name,
        mimetype=file_data.file_model.content_type,
        cache_timeout=-1,  # Don't cache these files on the browser.
        last_modified=file_data.date_created
    )


def get_file_info(file_id):
    file_model = session.query(FileModel).filter_by(id=file_id).with_for_update().first()
    if file_model is None:
        raise ApiError('no_such_file', 'The file id you provided does not exist', status_code=404)
    return FileSchema().dump(to_file_api(file_model))


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


def delete_file(file_id):
    FileService.delete_file(file_id)

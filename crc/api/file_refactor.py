from crc import session
from crc.api.common import ApiError
from crc.api.user import verify_token
from crc.models.file import DocumentModel, DocumentModelSchema, File, FileSchemaRefactor
from crc.models.workflow import WorkflowModel
from crc.services.document_service import DocumentService
from crc.services.study_service import StudyService
from crc.services.user_file_service import UserFileService

from flask import send_file

import connexion
import io


def to_file_api(document_model):
    # file_data_model = UserFileService.get_file_data(file_model.id)
    doc_dictionary = DocumentService.get_dictionary()
    return File.from_document_model(document_model, doc_dictionary)


def add_file(workflow_id=None, task_spec_name=None, irb_doc_code=None, study_id=None):
    file = connexion.request.files['file']
    if workflow_id:
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        if workflow is None:
            raise ApiError('invalid_workflow',
                           f'Unable to find a workflow with id {workflow_id}')
        if irb_doc_code is None:
            raise ApiError('invalid_doc_code',
                           'When adding a workflow related file, you must specify an irb_doc_code')
        if task_spec_name is None:
            raise ApiError('invalid_task_spec_name',
                           'When adding a workflow related file, you must specify a task_spec_name')
        file_model = UserFileService.add_workflow_file(workflow_id=workflow_id,
                                                                     irb_doc_code=irb_doc_code,
                                                                     task_spec_name=task_spec_name,
                                                                     name=file.filename,
                                                                     content_type=file.content_type,
                                                                     binary_data=file.stream.read())
        # We calculate the document statuses once per request, but a script may execute more quickly
        # So force a refresh of the document status here.
        # TODO: Finish refactoring this
        # StudyService.get_documents_status(study_id=workflow.study_id, force=True)
    else:
        raise ApiError('missing_workflow_id', 'You must supply a workflow_id.')

    return FileSchemaRefactor().dump(to_file_api(file_model))


def delete_file(file_id):
    UserFileService.delete_file(file_id)


def update_file_data(file_id):
    file_model = session.query(DocumentModel).filter_by(id=file_id).with_for_update().first()
    file = connexion.request.files['file']
    if file_model is None:
        raise ApiError('no_such_file', f'The file id you provided ({file_id}) does not exist')
    file_model = UserFileService.update_file(file_model, file.stream.read(), file.content_type)
    return FileSchemaRefactor().dump(to_file_api(file_model))


def get_files(workflow_id=None, form_field_key=None, study_id=None):
    if workflow_id is None:
        raise ApiError('missing_parameter',
                       'Please specify a workflow_id with an optional form_field_key')

    if study_id is not None:
        file_models = UserFileService.get_files_for_study(study_id=study_id, irb_doc_code=form_field_key)
    else:
        file_models = UserFileService.get_files(workflow_id=workflow_id,
                                            irb_doc_code=form_field_key)

    files = (to_file_api(model) for model in file_models)
    return FileSchemaRefactor(many=True).dump(files)


def get_file_data_by_hash(md5_hash):
    document_model = session.query(DocumentModel).filter(DocumentModel.md5_hash == md5_hash).first()
    if document_model is not None:
        return send_file(
            io.BytesIO(document_model.data),
            attachment_filename=document_model.name,
            mimetype=document_model.content_type,
            cache_timeout=-1  # Don't cache these files on the browser.
        )
    else:
        raise ApiError('missing_file_model', f'Could not find a document_model with the hash you provided.')


def get_file_data(document_id, version=None):
    document_model = session.query(DocumentModel).filter(DocumentModel.id==document_id).first()
    if document_model is not None:
        # file_data_model = UserFileService.get_file_data(file_id, version)
        # if file_data_model is not None:
        return send_file(
            io.BytesIO(document_model.data),
            attachment_filename=document_model.name,
            mimetype=document_model.content_type,
            cache_timeout=-1  # Don't cache these files on the browser.
        )
        # else:
        #     raise ApiError('missing_data_model', f'The data model for file ({file_id}) does not exist')
    else:
        raise ApiError('missing_file_model', f'The file id you provided ({document_id}) does not exist')


def get_file_data_link(file_id, auth_token, version=None):
    if not verify_token(auth_token):
        raise ApiError('not_authenticated', 'You need to include an authorization token in the URL with this')
    file_model = session.query(DocumentModel).filter(DocumentModel.id==file_id).first()
    # file_data = UserFileService.get_file_data(file_id, version)
    # if file_data is None:
    #     raise ApiError('no_such_file', f'The file id you provided ({file_id}) does not exist')
    if file_model is None:
        raise ApiError('no_such_file', f'The file id you provided ({file_id}) does not exist')
    return send_file(
        io.BytesIO(file_model.data),
        attachment_filename=file_model.name,
        mimetype=file_model.content_type,
        cache_timeout=-1,  # Don't cache these files on the browser.
        last_modified=file_model.date_created,
        as_attachment=True
    )


def get_file_info(file_id):
    file_model = session.query(DocumentModel).filter_by(id=file_id).with_for_update().first()
    if file_model is None:
        raise ApiError('no_such_file', f'The file id you provided ({file_id}) does not exist', status_code=404)
    return FileSchemaRefactor().dump(to_file_api(file_model))


def update_file_info(file_id, body):
    if file_id is None:
        raise ApiError('no_such_file', 'Please provide a valid File ID.')

    file_model = session.query(DocumentModel).filter_by(id=file_id).first()

    if file_model is None:
        raise ApiError('unknown_file_model', 'The file_model "' + file_id + '" is not recognized.')

    file_model = DocumentModelSchema().load(body, session=session)
    session.add(file_model)
    session.commit()
    return FileSchemaRefactor().dump(to_file_api(file_model))

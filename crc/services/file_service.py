import hashlib
import json
import os
from datetime import datetime
from uuid import UUID
from xml.etree import ElementTree

from pandas import ExcelFile

from crc import session
from crc.api.common import ApiError
from crc.models.file import FileType, FileDataModel, FileModel, LookupFileModel, LookupDataModel
from crc.models.workflow import WorkflowSpecModel
from crc.services.workflow_processor import WorkflowProcessor


class FileService(object):
    """Provides consistent management and rules for storing, retrieving and processing files."""
    DOCUMENT_LIST = "irb_documents.xlsx"
    INVESTIGATOR_LIST = "investigators.xlsx"

    @staticmethod
    def add_workflow_spec_file(workflow_spec: WorkflowSpecModel,
                               name, content_type, binary_data, primary=False, is_status=False):
        """Create a new file and associate it with a workflow spec."""
        file_model = FileModel(
            workflow_spec_id=workflow_spec.id,
            name=name,
            primary=primary,
            is_status=is_status,
        )

        return FileService.update_file(file_model, binary_data, content_type)

    @staticmethod
    def is_allowed_document(code):
        data_model = FileService.get_reference_file_data(FileService.DOCUMENT_LIST)
        xls = ExcelFile(data_model.data)
        df = xls.parse(xls.sheet_names[0])
        return code in df['code'].values

    @staticmethod
    def add_form_field_file(study_id, workflow_id, task_id, form_field_key, name, content_type, binary_data):
        """Create a new file and associate it with a user task form field within a workflow.
        Please note that the form_field_key MUST be a known file in the irb_documents.xslx reference document."""
        if not FileService.is_allowed_document(form_field_key):
            raise ApiError("invalid_form_field_key",
                           "When uploading files, the form field id must match a known document in the "
                           "irb_docunents.xslx reference file.  This code is not found in that file '%s'" % form_field_key)

        """Assure this is unique to the workflow, task, and document code AND the Name
           Because we will allow users to upload multiple files for the same form field 
            in some cases """
        file_model = session.query(FileModel)\
            .filter(FileModel.workflow_id == workflow_id)\
            .filter(FileModel.task_id == str(task_id))\
            .filter(FileModel.name == name)\
            .filter(FileModel.irb_doc_code == form_field_key).first()

        if not file_model:
            file_model = FileModel(
                study_id=study_id,
                workflow_id=workflow_id,
                task_id=task_id,
                name=name,
                form_field_key=form_field_key,
                irb_doc_code=form_field_key
            )
        return FileService.update_file(file_model, binary_data, content_type)

    @staticmethod
    def get_reference_data(reference_file_name, index_column, int_columns=[]):
        """ Opens a reference file (assumes that it is xls file) and returns the data as a
        dictionary, each row keyed on the given index_column name. If there are columns
          that should be represented as integers, pass these as an array of int_columns, lest
          you get '1.0' rather than '1' """
        data_model = FileService.get_reference_file_data(reference_file_name)
        xls = ExcelFile(data_model.data)
        df = xls.parse(xls.sheet_names[0])
        for c in int_columns:
            df[c] = df[c].fillna(0)
            df = df.astype({c: 'Int64'})
        df = df.fillna('')
        df = df.applymap(str)
        df = df.set_index(index_column)
        return json.loads(df.to_json(orient='index'))

    @staticmethod
    def add_task_file(study_id, workflow_id, workflow_spec_id, task_id, name, content_type, binary_data,
                      irb_doc_code=None):

        """Assure this is unique to the workflow, task, and document code.  Disregard name."""
        file_model = session.query(FileModel)\
            .filter(FileModel.workflow_id == workflow_id)\
            .filter(FileModel.task_id == str(task_id))\
            .filter(FileModel.irb_doc_code == irb_doc_code).first()

        if not file_model:
            """Create a new file and associate it with an executing task within a workflow."""
            file_model = FileModel(
                study_id=study_id,
                workflow_id=workflow_id,
                workflow_spec_id=workflow_spec_id,
                task_id=task_id,
                name=name,
                irb_doc_code=irb_doc_code
            )
        return FileService.update_file(file_model, binary_data, content_type)

    @staticmethod
    def get_workflow_files(workflow_id):
        """Returns all the file models associated with a running workflow."""
        return session.query(FileModel).filter(FileModel.workflow_id == workflow_id).\
            order_by(FileModel.id).all()

    @staticmethod
    def add_reference_file(name, content_type, binary_data):
        """Create a file with the given name, but not associated with a spec or workflow.
           Only one file with the given reference name can exist."""
        file_model = session.query(FileModel). \
            filter(FileModel.is_reference == True). \
            filter(FileModel.name == name).first()
        if not file_model:
            file_model = FileModel(
                name=name,
                is_reference=True
            )
        return FileService.update_file(file_model, binary_data, content_type)

    @staticmethod
    def get_extension(file_name):
        basename, file_extension = os.path.splitext(file_name)
        return file_extension.lower().strip()[1:]

    @staticmethod

    def update_file(file_model, binary_data, content_type):
        session.flush()  # Assure the database is up-to-date before running this.

        file_data_model = session.query(FileDataModel). \
            filter_by(file_model_id=file_model.id,
                      version=file_model.latest_version
                      ).with_for_update().first()
        md5_checksum = UUID(hashlib.md5(binary_data).hexdigest())
        if (file_data_model is not None) and (md5_checksum == file_data_model.md5_hash):
            # This file does not need to be updated, it's the same file.
            return file_model

        # Verify the extension
        file_extension = FileService.get_extension(file_model.name)
        if file_extension not in FileType._member_names_:
            raise ApiError('unknown_extension',
                           'The file you provided does not have an accepted extension:' +
                           file_extension, status_code=404)
        else:
            file_model.type = FileType[file_extension]
            file_model.content_type = content_type

        if file_data_model is None:
            version = 1
        else:
            version = file_data_model.version + 1

        # If this is a BPMN, extract the process id.
        if file_model.type == FileType.bpmn:
            bpmn: ElementTree.Element = ElementTree.fromstring(binary_data)
            file_model.primary_process_id = WorkflowProcessor.get_process_id(bpmn)

        file_model.latest_version = version
        new_file_data_model = FileDataModel(
            data=binary_data, file_model_id=file_model.id, file_model=file_model,
            version=version, md5_hash=md5_checksum, last_updated=datetime.now()
        )

        session.add_all([file_model, new_file_data_model])
        session.commit()
        session.flush()  # Assure the id is set on the model before returning it.

        return file_model

    @staticmethod
    def get_files(workflow_spec_id=None,
                  study_id=None, workflow_id=None, task_id=None, form_field_key=None,
                  name=None, is_reference=False, irb_doc_code=None):
        query = session.query(FileModel).filter_by(is_reference=is_reference)
        if workflow_spec_id:
            query = query.filter_by(workflow_spec_id=workflow_spec_id)
        if all(v is None for v in [study_id, workflow_id, task_id, form_field_key]):
            query = query.filter_by(
                study_id=None,
                workflow_id=None,
                task_id=None,
                form_field_key=None,
            )
        else:
            if study_id:
                query = query.filter_by(study_id=study_id)
            if workflow_id:
                query = query.filter_by(workflow_id=workflow_id)
            if task_id:
                query = query.filter_by(task_id=str(task_id))
            if form_field_key:
                query = query.filter_by(form_field_key=form_field_key)
            if name:
                query = query.filter_by(name=name)
            if irb_doc_code:
                query = query.filter_by(irb_doc_code=irb_doc_code)

        results = query.all()
        return results

    @staticmethod
    def get_file_data(file_id, file_model=None, version=None):

        """Returns the file_data that is associated with the file model id, if an actual file_model
        is provided, uses that rather than looking it up again."""
        if file_model is None:
            file_model = session.query(FileModel).filter(FileModel.id == file_id).first()
        if version is None:
            version = file_model.latest_version
        return session.query(FileDataModel) \
            .filter(FileDataModel.file_model_id == file_id) \
            .filter(FileDataModel.version == version) \
            .first()

    @staticmethod
    def get_reference_file_data(file_name):
        file_model = session.query(FileModel). \
            filter(FileModel.is_reference == True). \
            filter(FileModel.name == file_name).first()
        if not file_model:
            raise ApiError("file_not_found", "There is no reference file with the name '%s'" % file_name)
        return FileService.get_file_data(file_model.id, file_model)

    @staticmethod
    def get_workflow_file_data(workflow, file_name):
        """Given a SPIFF Workflow Model, tracks down a file with the given name in the database and returns its data"""
        workflow_spec_model = FileService.find_spec_model_in_db(workflow)

        if workflow_spec_model is None:
            raise ApiError(code="workflow_model_error",
                           message="Something is wrong.  I can't find the workflow you are using.")

        file_data_model = session.query(FileDataModel) \
            .join(FileModel) \
            .filter(FileModel.name == file_name) \
            .filter(FileModel.workflow_spec_id == workflow_spec_model.id).first()

        if file_data_model is None:
            raise ApiError(code="file_missing",
                           message="Can not find a file called '%s' within workflow specification '%s'"
                                   % (file_name, workflow_spec_model.id))

        return file_data_model

    @staticmethod
    def find_spec_model_in_db(workflow):
        """ Search for the workflow """
        # When the workflow spec model is created, we record the primary process id,
        # then we can look it up.  As there is the potential for sub-workflows, we
        # may need to travel up to locate the primary process.
        spec = workflow.spec
        workflow_model = session.query(WorkflowSpecModel).join(FileModel). \
            filter(FileModel.primary_process_id == spec.name).first()
        if workflow_model is None and workflow != workflow.outer_workflow:
            return FileService.find_spec_model_in_db(workflow.outer_workflow)

        return workflow_model

    @staticmethod
    def delete_file(file_id):
        data_models = session.query(FileDataModel).filter_by(file_model_id=file_id).all()
        for dm in data_models:
            lookup_files = session.query(LookupFileModel).filter_by(file_data_model_id=dm.id).all()
            for lf in lookup_files:
                session.query(LookupDataModel).filter_by(lookup_file_model_id=lf.id).delete()
                session.query(LookupFileModel).filter_by(id=lf.id).delete()
        session.query(FileDataModel).filter_by(file_model_id=file_id).delete()
        session.query(FileModel).filter_by(id=file_id).delete()
        session.commit()

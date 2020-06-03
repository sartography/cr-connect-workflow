import hashlib
import json
import os
from datetime import datetime
from uuid import UUID
from xml.etree import ElementTree

import flask
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from pandas import ExcelFile
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from crc import session, app
from crc.api.common import ApiError
from crc.models.file import FileType, FileDataModel, FileModel, LookupFileModel, LookupDataModel
from crc.models.workflow import WorkflowSpecModel, WorkflowModel, WorkflowSpecDependencyFile


class FileService(object):
    """Provides consistent management and rules for storing, retrieving and processing files."""
    DOCUMENT_LIST = "irb_documents.xlsx"
    INVESTIGATOR_LIST = "investigators.xlsx"

    __doc_dictionary = None

    @staticmethod
    def get_doc_dictionary():
        if not FileService.__doc_dictionary:
            FileService.__doc_dictionary = FileService.get_reference_data(FileService.DOCUMENT_LIST, 'code', ['id'])
        return FileService.__doc_dictionary

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
    def add_workflow_file(workflow_id, irb_doc_code, name, content_type, binary_data):
        """Create a new file and associate it with the workflow
        Please note that the irb_doc_code MUST be a known file in the irb_documents.xslx reference document."""
        if not FileService.is_allowed_document(irb_doc_code):
            raise ApiError("invalid_form_field_key",
                           "When uploading files, the form field id must match a known document in the "
                           "irb_docunents.xslx reference file.  This code is not found in that file '%s'" % irb_doc_code)

        """Assure this is unique to the workflow, task, and document code AND the Name
           Because we will allow users to upload multiple files for the same form field 
            in some cases """
        file_model = session.query(FileModel)\
            .filter(FileModel.workflow_id == workflow_id)\
            .filter(FileModel.name == name)\
            .filter(FileModel.irb_doc_code == irb_doc_code).first()

        if not file_model:
            file_model = FileModel(
                workflow_id=workflow_id,
                name=name,
                irb_doc_code=irb_doc_code
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

        latest_data_model = session.query(FileDataModel). \
            filter(FileDataModel.file_model_id == file_model.id).\
            order_by(desc(FileDataModel.date_created)).first()

        md5_checksum = UUID(hashlib.md5(binary_data).hexdigest())
        if (latest_data_model is not None) and (md5_checksum == latest_data_model.md5_hash):
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

        if latest_data_model is None:
            version = 1
        else:
            version = latest_data_model.version + 1

        # If this is a BPMN, extract the process id.
        if file_model.type == FileType.bpmn:
            bpmn: ElementTree.Element = ElementTree.fromstring(binary_data)
            file_model.primary_process_id = FileService.get_process_id(bpmn)

        new_file_data_model = FileDataModel(
            data=binary_data, file_model_id=file_model.id, file_model=file_model,
            version=version, md5_hash=md5_checksum, date_created=datetime.now()
        )
        session.add_all([file_model, new_file_data_model])
        session.commit()
        session.flush()  # Assure the id is set on the model before returning it.

        return file_model

    @staticmethod
    def get_process_id(et_root: ElementTree.Element):
        process_elements = []
        for child in et_root:
            if child.tag.endswith('process') and child.attrib.get('isExecutable', False):
                process_elements.append(child)

        if len(process_elements) == 0:
            raise ValidationException('No executable process tag found')

        # There are multiple root elements
        if len(process_elements) > 1:

            # Look for the element that has the startEvent in it
            for e in process_elements:
                this_element: ElementTree.Element = e
                for child_element in list(this_element):
                    if child_element.tag.endswith('startEvent'):
                        return this_element.attrib['id']

            raise ValidationException('No start event found in %s' % et_root.attrib['id'])

        return process_elements[0].attrib['id']

    @staticmethod
    def get_files_for_study(study_id, irb_doc_code=None):
        query = session.query(FileModel).\
                join(WorkflowModel).\
                filter(WorkflowModel.study_id == study_id)
        if irb_doc_code:
            query = query.filter(FileModel.irb_doc_code == irb_doc_code)
        return query.all()

    @staticmethod
    def get_files(workflow_spec_id=None, workflow_id=None,
                  name=None, is_reference=False, irb_doc_code=None):
        query = session.query(FileModel).filter_by(is_reference=is_reference)
        if workflow_spec_id:
            query = query.filter_by(workflow_spec_id=workflow_spec_id)
        elif workflow_id:
            query = query.filter_by(workflow_id=workflow_id)
            if irb_doc_code:
                query = query.filter_by(irb_doc_code=irb_doc_code)
        elif is_reference:
            query = query.filter_by(is_reference=True)

        if name:
            query = query.filter_by(name=name)
        query = query.order_by(FileModel.id)

        results = query.all()
        return results

    @staticmethod
    def get_spec_data_files(workflow_spec_id, workflow_id=None, name=None):
        """Returns all the FileDataModels related to a workflow specification.
        If a workflow is specified, returns the version of the spec relatted
        to that workflow, otherwise, returns the lastes files."""
        if workflow_id:
            query = session.query(FileDataModel) \
                    .join(WorkflowSpecDependencyFile) \
                    .filter(WorkflowSpecDependencyFile.workflow_id == workflow_id) \
                    .order_by(FileDataModel.id)
            if name:
                query = query.join(FileModel).filter(FileModel.name == name)
            return query.all()
        else:
            """Returns all the latest files related to a workflow specification"""
            file_models = FileService.get_files(workflow_spec_id=workflow_spec_id)
            latest_data_files = []
            for file_model in file_models:
                if name and file_model.name == name:
                    latest_data_files.append(FileService.get_file_data(file_model.id))
                elif not name:
                    latest_data_files.append(FileService.get_file_data(file_model.id))
            return latest_data_files

    @staticmethod
    def get_workflow_data_files(workflow_id=None):
        """Returns all the FileDataModels related to a running workflow -
        So these are the latest data files that were uploaded or generated
        that go along with this workflow.  Not related to the spec in any way"""
        file_models = FileService.get_files(workflow_id=workflow_id)
        latest_data_files = []
        for file_model in file_models:
            latest_data_files.append(FileService.get_file_data(file_model.id))
        return latest_data_files

    @staticmethod
    def get_file_data(file_id: int, version: int = None):
        """Returns the file data with the given version, or the lastest file, if version isn't provided."""
        query = session.query(FileDataModel) \
            .filter(FileDataModel.file_model_id == file_id)
        if version:
            query = query.filter(FileDataModel.version == version)
        else:
            query = query.order_by(desc(FileDataModel.date_created))
        return query.first()

    @staticmethod
    def get_reference_file_data(file_name):
        file_model = session.query(FileModel). \
            filter(FileModel.is_reference == True). \
            filter(FileModel.name == file_name).first()
        if not file_model:
            raise ApiError("file_not_found", "There is no reference file with the name '%s'" % file_name)
        return FileService.get_file_data(file_model.id)

    @staticmethod
    def get_workflow_file_data(workflow, file_name):
        """Given a SPIFF Workflow Model, tracks down a file with the given name in the database and returns its data"""
        workflow_spec_model = FileService.find_spec_model_in_db(workflow)

        if workflow_spec_model is None:
            raise ApiError(code="unknown_workflow",
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
        try:
            data_models = session.query(FileDataModel).filter_by(file_model_id=file_id).all()
            for dm in data_models:
                lookup_files = session.query(LookupFileModel).filter_by(file_data_model_id=dm.id).all()
                for lf in lookup_files:
                    session.query(LookupDataModel).filter_by(lookup_file_model_id=lf.id).delete()
                    session.query(LookupFileModel).filter_by(id=lf.id).delete()
            session.query(FileDataModel).filter_by(file_model_id=file_id).delete()
            session.query(FileModel).filter_by(id=file_id).delete()
            session.commit()
        except IntegrityError as ie:
            app.logger.error("Failed to delete file: %i, due to %s" % (file_id, str(ie)))
            raise ApiError('file_integrity_error', "You are attempting to delete a file that is "
                                                   "required by other records in the system.")
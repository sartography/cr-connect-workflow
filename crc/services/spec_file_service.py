import hashlib
import json
import os

from crc import app, session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileModelSchema, FileDataModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecCategoryModel
from crc.services.file_service import FileService, FileType

from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException

from lxml import etree
from sqlalchemy.exc import IntegrityError
from uuid import UUID


class SpecFileService(object):

    @staticmethod
    def add_workflow_spec_file(workflow_spec: WorkflowSpecModel,
                               name, content_type, binary_data, primary=False, is_status=False):
        """Create a new file and associate it with a workflow spec."""
        file_model = session.query(FileModel)\
            .filter(FileModel.workflow_spec_id == workflow_spec.id)\
            .filter(FileModel.name == name).first()

        if file_model:
            if not file_model.archived:
                # Raise ApiError if the file already exists and is not archived
                raise ApiError(code="duplicate_file",
                               message='If you want to replace the file, use the update mechanism.')
        else:
            file_model = FileModel(
                workflow_spec_id=workflow_spec.id,
                name=name,
                primary=primary,
                is_status=is_status,
            )

        return SpecFileService.update_workflow_spec_file(workflow_spec, file_model, binary_data, content_type)


    @staticmethod
    def get_sync_file_root():
        dir_name = app.config['SYNC_FILE_ROOT']
        app_root = app.root_path
        return os.path.join(app_root, '..', 'tests', dir_name)

    def write_file_to_system(self, workflow_spec_model, file_model, file_data):

        category_name = None
        sync_file_root = self.get_sync_file_root()

        # if file_model.workflow_spec_id is not None:
        #     # we have a workflow spec file
        #     workflow_spec_model = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id == file_model.workflow_spec_id).first()
        #     if workflow_spec_model:

        if workflow_spec_model is not None:
            category_name = self.get_spec_file_category_name(workflow_spec_model)
        if category_name is None and file_model.is_reference:
            category_name = 'Reference'


        # if workflow_spec_model.category_id is not None:
        #     category_name = session.query(WorkflowSpecCategoryModel.display_name).filter(WorkflowSpecCategoryModel.id == workflow_spec_model.category_id).scalar()
        #
        # elif workflow_spec_model.is_master_spec:
        #     category_name = 'Master Specification'
        #
        # elif workflow_spec_model.library:
        #     category_name = 'Library Specs'

        if category_name is not None:
            if workflow_spec_model is not None:
                file_path = os.path.join(sync_file_root,
                                         category_name,
                                         workflow_spec_model.display_name,
                                         file_model.name)
            else:
                # Reference files all sit in the 'Reference' directory
                file_path = os.path.join(sync_file_root,
                                         category_name,
                                         file_model.name)

            # self.process_workflow_spec_file(file_model, file_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f_handle:
                f_handle.write(file_data)
            json_file_path = f'{file_path}.json'
            latest_file_model = session.query(FileModel).filter(FileModel.id==file_model.id).first()
            file_schema = FileModelSchema().dumps(latest_file_model)
            with open(json_file_path, 'w') as j_handle:
                j_handle.write(file_schema)

    @staticmethod
    def update_workflow_spec_file(workflow_spec, file_model, binary_data, content_type):
        # Verify the extension
        file_extension = FileService.get_extension(file_model.name)
        if file_extension not in FileType._member_names_:
            raise ApiError('unknown_extension',
                           'The file you provided does not have an accepted extension:' +
                           file_extension, status_code=404)
        else:
            file_model.type = FileType[file_extension]
            file_model.content_type = content_type
            file_model.archived = False  # Unarchive the file if it is archived.

        # If this is a BPMN, extract the process id.
        if file_model.type == FileType.bpmn:
            try:
                bpmn: etree.Element = etree.fromstring(binary_data)
                file_model.primary_process_id = SpecFileService.get_process_id(bpmn)
                file_model.is_review = FileService.has_swimlane(bpmn)
            except etree.XMLSyntaxError as xse:
                raise ApiError("invalid_xml", "Failed to parse xml: " + str(xse), file_name=file_model.name)

        session.add(file_model)
        session.commit()

        # Write file to filesystem
        SpecFileService().write_file_to_system(workflow_spec, file_model, binary_data)
        return file_model

    @staticmethod
    def get_workflow_spec_category_name(workflow_spec_id):
        category_name = None
        workflow_spec = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id==workflow_spec_id).first()
        category_id = workflow_spec.category_id
        if category_id is not None:
            category_name = session.query(WorkflowSpecCategoryModel.display_name).filter(WorkflowSpecCategoryModel.id==category_id).scalar()
        elif workflow_spec.is_master_spec:
            category_name = 'Master Specification'
        elif workflow_spec.library:
            category_name = 'Library Specs'
        elif workflow_spec.standalone:
            category_name = 'Standalone'
        return category_name

    def get_spec_data_files(self, workflow_spec_id, workflow_id=None, name=None, include_libraries=False):
        """Returns all the files related to a workflow specification.
        if `name` is included we only return the file with that name"""
        spec_data_files = []
        workflow_spec = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id==workflow_spec_id).first()
        workflow_spec_name = workflow_spec.display_name
        category_name = self.get_workflow_spec_category_name(workflow_spec_id)
        sync_file_root = self.get_sync_file_root()
        spec_path = os.path.join(sync_file_root,
                                 category_name,
                                 workflow_spec_name)
        directory_items = os.scandir(spec_path)
        for item in directory_items:
            if item.is_file() and not item.name.endswith('json'):
                if name is not None and item.name != name:
                    continue
                with open(item.path, 'rb') as f_open:
                    json_path = f'{item.path}.json'
                    with open(json_path, 'r') as j_open:
                        json_data = j_open.read()
                        json_obj = json.loads(json_data)
                        file_data = f_open.read()
                        file_dict = {'meta': json_obj,
                                     'data': file_data}
                        spec_data_files.append(file_dict)
        print('get_spec_data_files')
        return spec_data_files
        # if workflow_id:
        #     query = session.query(FileDataModel) \
        #             .join(WorkflowSpecDependencyFile) \
        #             .filter(WorkflowSpecDependencyFile.workflow_id == workflow_id) \
        #             .order_by(FileDataModel.id)
        #     if name:
        #         query = query.join(FileModel).filter(FileModel.name == name)
        #     return query.all()
        # else:
        #     """Returns all the latest files related to a workflow specification"""
        #     file_models = FileService.get_files(workflow_spec_id=workflow_spec_id,include_libraries=include_libraries)
        #     latest_data_files = []
        #     for file_model in file_models:
        #         if name and file_model.name == name:
        #             latest_data_files.append(FileService.get_file_data(file_model.id))
        #         elif not name:
        #             latest_data_files.append(FileService.get_file_data(file_model.id))
        #     return latest_data_files

    @staticmethod
    def get_spec_file_category_name(spec_model):
        category_name = None
        if hasattr(spec_model, 'category_id') and spec_model.category_id is not None:
            category_model = session.query(WorkflowSpecCategoryModel).\
                filter(WorkflowSpecCategoryModel.id == spec_model.category_id).\
                first()
            category_name = category_model.display_name

        elif spec_model.is_master_spec:
            category_name = 'Master Specification'

        elif spec_model.library:
            category_name = 'Library Specs'

        elif spec_model.standalone:
            category_name = 'Standalone'

        return category_name

    def get_spec_file_data(self, file_id: int):
        file_model = session.query(FileModel).filter(FileModel.id==file_id).first()
        if file_model is not None:
            spec_model = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id==file_model.workflow_spec_id).first()
            if spec_model is not None:
                category_name = self.get_spec_file_category_name(spec_model)
                sync_file_root = self.get_sync_file_root()
                file_path = os.path.join(sync_file_root, category_name, spec_model.display_name, file_model.name)
                stats = os.stat(file_path)
                with open(file_path, 'rb') as f_handle:
                    spec_file_data = f_handle.read()
                    size = len(spec_file_data)
                    md5_checksum = UUID(hashlib.md5(spec_file_data).hexdigest())

                    file_data_model = FileDataModel(data=spec_file_data,
                                                    md5_hash=md5_checksum,
                                                    size=size,
                                                    date_created=stats.st_mtime,
                                                    file_model_id=file_id)
                    return file_data_model
            else:
                raise ApiError(code='spec_not_found',
                               message=f'No spec found for file with file_id: {file_id}, and spec_id: {file_model.workflow_spec_id}')
        else:
            raise ApiError(code='model_not_found',
                           message=f'No model found for file with file_id: {file_id}')

    @staticmethod
    def delete_spec_file(file_id):
        sync_file_root = SpecFileService.get_sync_file_root()
        file_model = session.query(FileModel).filter(FileModel.id==file_id).first()
        workflow_spec_id = file_model.workflow_spec_id
        workflow_spec_model = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id==workflow_spec_id).first()
        category_name = SpecFileService.get_spec_file_category_name(workflow_spec_model)
        file_model_name = file_model.name
        spec_directory_path = os.path.join(sync_file_root,
                                           category_name,
                                           workflow_spec_model.display_name)
        file_path = os.path.join(spec_directory_path,
                                 file_model_name)
        json_file_path = os.path.join(spec_directory_path,
                                      f'{file_model_name}.json')

        try:
            os.remove(file_path)
            os.remove(json_file_path)
            # os.rmdir(spec_directory_path)
            session.delete(file_model)
            session.commit()
        except IntegrityError as ie:
            session.rollback()
            file_model = session.query(FileModel).filter_by(id=file_id).first()
            file_model.archived = True
            session.commit()
            app.logger.info("Failed to delete file, so archiving it instead. %i, due to %s" % (file_id, str(ie)))

    @staticmethod
    def get_process_id(et_root: etree.Element):
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
                this_element: etree.Element = e
                for child_element in list(this_element):
                    if child_element.tag.endswith('startEvent'):
                        return this_element.attrib['id']

            raise ValidationException('No start event found in %s' % et_root.attrib['id'])

        return process_elements[0].attrib['id']

    #
    # Reference File Methods
    #

    @staticmethod
    def add_reference_file(name, content_type, binary_data):
        """Create a file with the given name, but not associated with a spec or workflow.
           Only one file with the given reference name can exist."""
        file_model = session.query(FileModel). \
            filter(FileModel.is_reference == True). \
            filter(FileModel.name == name).first()
        if not file_model:
            file_extension = FileService.get_extension(name)
            file_type = FileType[file_extension].value

            file_model = FileModel(
                name=name,
                is_reference=True,
                type=file_type,
                content_type=content_type
            )
        return SpecFileService().update_reference_file(file_model, binary_data, content_type)

    def update_reference_file(self, file_model, binary_data, content_type):
        session.add(file_model)
        session.commit()
        self.write_file_to_system(None, file_model, binary_data)
        print('update_reference_file')
        return file_model

    @staticmethod
    def get_reference_file_data(file_name):
        sync_file_root = SpecFileService().get_sync_file_root()
        file_path = os.path.join(sync_file_root, 'Reference', file_name)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f_open:
                file_data = f_open.read()
                return file_data
        else:
            raise ApiError("file_not_found", "There is no reference file with the name '%s'" % file_name)


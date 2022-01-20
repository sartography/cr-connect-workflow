import hashlib
import json
import datetime
import os

from crc import app, session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileModelSchema, FileDataModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecCategoryModel, WorkflowLibraryModel
from crc.services.file_service import FileService, FileType

from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException

from lxml import etree
from sqlalchemy.exc import IntegrityError
from uuid import UUID


class SpecFileService(object):

    """We store spec files on the file system. This allows us to take advantage of Git for
       syncing and versioning.

        We keep a record in the File table, but do not have a record in the FileData table.

        For syncing purposes, we keep a copy of the File table info in a json file

        This means there are 3 pieces we have to maintain; File table record, file on the file system,
        and json file on the file system.

        The files are stored in a directory whose path is determined by the category and spec names.
    """

    #
    # Shared Methods
    #
    @staticmethod
    def get_sync_file_root():
        dir_name = app.config['SYNC_FILE_ROOT']
        app_root = app.root_path
        return os.path.join(app_root, '..', dir_name)

    @staticmethod
    def get_path_from_spec_file_model(spec_file_model):
        workflow_spec_model = session.query(WorkflowSpecModel).filter(
            WorkflowSpecModel.id == spec_file_model.workflow_spec_id).first()
        category_name = SpecFileService.get_spec_file_category_name(workflow_spec_model)
        if category_name is not None:
            sync_file_root = SpecFileService.get_sync_file_root()
            file_path = os.path.join(sync_file_root,
                                     category_name,
                                     workflow_spec_model.display_name,
                                     spec_file_model.name)
            return file_path

    @staticmethod
    def write_file_data_to_system(file_path, file_data):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f_handle:
            f_handle.write(file_data)

    @staticmethod
    def write_file_info_to_system(file_path, file_model):
        json_file_path = f'{file_path}.json'
        latest_file_model = session.query(FileModel).filter(FileModel.id == file_model.id).first()
        file_schema = FileModelSchema().dumps(latest_file_model)
        with open(json_file_path, 'w') as j_handle:
            j_handle.write(file_schema)

    #
    # Workflow Spec Methods
    #
    @staticmethod
    def add_workflow_spec_file(workflow_spec: WorkflowSpecModel,
                               name, content_type, binary_data, primary=False, is_status=False):
        """Create a new file and associate it with a workflow spec.
        3 steps; create file model, write file data to filesystem, write file info to file system"""
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

        file_model = SpecFileService.update_workflow_spec_file_model(workflow_spec, file_model, binary_data, content_type)
        file_path = SpecFileService().write_spec_file_data_to_system(workflow_spec, file_model.name, binary_data)
        SpecFileService().write_spec_file_info_to_system(file_path, file_model)

        return file_model

    def update_workflow_spec_file(self, workflow_spec_model, file_model, file_data, content_type):
        self.update_workflow_spec_file_model(workflow_spec_model, file_model, file_data, content_type)
        self.update_spec_file_data(workflow_spec_model, file_model.name, file_data)
        self.update_spec_file_info()

    @staticmethod
    def update_workflow_spec_file_model(workflow_spec: WorkflowSpecModel, file_model: FileModel, binary_data, content_type):
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

        return file_model

    @staticmethod
    def update_spec_file_data(workflow_spec, file_name, binary_data):
        file_path = SpecFileService().write_spec_file_data_to_system(workflow_spec, file_name, binary_data)
        return file_path

    def update_spec_file_info(self, old_file_model, body):

        file_data = self.get_spec_file_data(old_file_model.id)

        old_file_path = self.get_path_from_spec_file_model(old_file_model)
        self.delete_spec_file_data(old_file_path)
        self.delete_spec_file_info(old_file_path)

        new_file_model = FileModelSchema().load(body, session=session)
        new_file_path = self.get_path_from_spec_file_model(new_file_model)
        self.write_file_data_to_system(new_file_path, file_data.data)
        self.write_file_info_to_system(new_file_path, new_file_model)
        print('update_spec_file_info')
        return new_file_model

    @staticmethod
    def delete_spec_file_data(file_path):
        os.remove(file_path)

    @staticmethod
    def delete_spec_file_info(file_path):
        json_file_path = f'{file_path}.json'
        os.remove(json_file_path)

    # Placeholder. Not sure if we need this.
    # Might do this work in delete_spec_file
    def delete_spec_file_model(self):
        pass

    @staticmethod
    def delete_spec_file(file_id):
        """This should remove the record in the file table, and both files on the filesystem."""
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
            session.delete(file_model)
            session.commit()
        except IntegrityError as ie:
            session.rollback()
            file_model = session.query(FileModel).filter_by(id=file_id).first()
            file_model.archived = True
            session.commit()
            app.logger.info("Failed to delete file, so archiving it instead. %i, due to %s" % (file_id, str(ie)))

    def write_spec_file_data_to_system(self, workflow_spec_model, file_name, file_data):
        if workflow_spec_model is not None:
            category_name = self.get_spec_file_category_name(workflow_spec_model)
            if category_name is not None:
                sync_file_root = self.get_sync_file_root()
                file_path = os.path.join(sync_file_root,
                                         category_name,
                                         workflow_spec_model.display_name,
                                         file_name)
                self.write_file_data_to_system(file_path, file_data)
                return file_path

    def write_spec_file_info_to_system(self, file_path, file_model):
        self.write_file_info_to_system(file_path, file_model)
        # json_file_path = f'{file_path}.json'
        # latest_file_model = session.query(FileModel).filter(FileModel.id == file_model.id).first()
        # file_schema = FileModelSchema().dumps(latest_file_model)
        # with open(json_file_path, 'w') as j_handle:
        #     j_handle.write(file_schema)

    def write_spec_file_to_system(self, workflow_spec_model, file_model, file_data):
        file_path = self.write_spec_file_data_to_system(workflow_spec_model, file_model, file_data)
        self.write_spec_file_info_to_system(file_path, file_model)

    def get_spec_data_files(self, workflow_spec_id, workflow_id=None, name=None, include_libraries=False):
        """Returns all the files related to a workflow specification.
        if `name` is included we only return the file with that name"""
        spec_data_files = []
        workflow_spec = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id==workflow_spec_id).first()
        workflow_spec_name = workflow_spec.display_name
        category_name = self.get_spec_file_category_name(workflow_spec)
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

    def get_path(self, file_id: int):
        # Returns the path on the file system for the given File id

        # Assure we have a file.
        file_model = session.query(FileModel).filter(FileModel.id==file_id).first()
        if not file_model:
            raise ApiError(code='model_not_found',
                           message=f'No model found for file with file_id: {file_id}')

        # Assure we have a spec.
        spec_model = session.query(WorkflowSpecModel).filter(
            WorkflowSpecModel.id == file_model.workflow_spec_id).first()
        if not spec_model:
            raise ApiError(code='spec_not_found',
                       message=f'No spec found for file with file_id: '
                               f'{file_model.id}, and spec_id: {file_model.workflow_spec_id}')

        # Calculate the path.
        sync_file_root = self.get_sync_file_root()
        category_name = self.get_spec_file_category_name(spec_model)
        return os.path.join(sync_file_root, category_name, spec_model.display_name, file_model.name)


    def last_modified(self, file_id: int):
        path = self.get_path(file_id)
        return self.__last_modified(path)

    def __last_modified(self, file_path: str):
        # Returns the last modified date of the given file.
        timestamp = os.path.getmtime(file_path)
        return datetime.datetime.fromtimestamp(timestamp)

    def get_spec_file_data(self, file_id: int):
        file_path = self.get_path(file_id)
        date = self.last_modified(file_id)
        with open(file_path, 'rb') as f_handle:
            spec_file_data = f_handle.read()
            size = len(spec_file_data)
            md5_checksum = UUID(hashlib.md5(spec_file_data).hexdigest())
            last_modified = self.__last_modified(file_path)
            file_data_model = FileDataModel(data=spec_file_data,
                                            md5_hash=md5_checksum,
                                            size=size,
                                            date_created=last_modified,
                                            file_model_id=file_id)
            return file_data_model


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

    @staticmethod
    def get_spec_files(workflow_spec_id, include_libraries=False):
        if workflow_spec_id:
            if include_libraries:
                libraries = session.query(WorkflowLibraryModel).filter(
                   WorkflowLibraryModel.workflow_spec_id==workflow_spec_id).all()
                library_workflow_specs = [x.library_spec_id for x in libraries]
                library_workflow_specs.append(workflow_spec_id)
                query = session.query(FileModel).filter(FileModel.workflow_spec_id.in_(library_workflow_specs))
            else:
                query = session.query(FileModel).filter(FileModel.workflow_spec_id == workflow_spec_id)

            query = query.filter(FileModel.archived == False)
            query = query.order_by(FileModel.id)

            results = query.all()
            return results

    @staticmethod
    def get_workflow_file_data(workflow, file_name):
        """This method should be deleted, find where it is used, and remove this method.
        Given a SPIFF Workflow Model, tracks down a file with the given name in the database and returns its data"""
        workflow_spec_model = SpecFileService.find_spec_model_in_db(workflow)

        if workflow_spec_model is None:
            raise ApiError(code="unknown_workflow",
                           message="Something is wrong.  I can't find the workflow you are using.")
        file_id = session.query(FileModel.id).filter(FileModel.workflow_spec_id==workflow_spec_model.id).filter(FileModel.name==file_name).scalar()
        file_data_model = SpecFileService().get_spec_file_data(file_id)

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
            return SpecFileService.find_spec_model_in_db(workflow.outer_workflow)

        return workflow_model

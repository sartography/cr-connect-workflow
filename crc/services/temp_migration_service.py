# from crc import app, session
from crc.models.file import FileModel, FileModelSchema, FileDataModel, CONTENT_TYPES
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowSpecCategoryModel, WorkflowSpecCategoryModelSchema
from crc.services.file_service import FileService
from crc.services.spec_file_service import SpecFileService
from crc.services.workflow_service import WorkflowService
from sqlalchemy import desc

import json
import os


# SYNC_FILE_ROOT = SpecFileService.get_sync_file_root()


class FromFilesystemService(object):

    @staticmethod
    def process_directory(directory):
        files = []
        directories = []
        directory_items = os.scandir(directory)
        for item in directory_items:
            if item.is_dir():
                directories.append(item)
            elif item.is_file():
                files.append(item)

        return files, directories

    @staticmethod
    def process_workflow_spec(json_file, directory):
        file_path = os.path.join(directory, json_file)

        with open(file_path, 'r') as f_open:
            data = f_open.read()
            data_obj = json.loads(data)
            workflow_spec_model = session.query(WorkflowSpecModel).\
                filter(WorkflowSpecModel.id == data_obj['id']).\
                first()
            if not workflow_spec_model:
                category_id = None
                if data_obj['category'] is not None:
                    category_id = session.query(WorkflowSpecCategoryModel.id).filter(
                        WorkflowSpecCategoryModel.display_name == data_obj['category']['display_name']).scalar()
                workflow_spec_model = WorkflowSpecModel(id=data_obj['id'],
                                                        display_name=data_obj['display_name'],
                                                        description=data_obj['description'],
                                                        is_master_spec=data_obj['is_master_spec'],
                                                        category_id=category_id,
                                                        display_order=data_obj['display_order'],
                                                        standalone=data_obj['standalone'],
                                                        library=data_obj['library'])
                session.add(workflow_spec_model)
                session.commit()

            return workflow_spec_model

    @staticmethod
    def process_workflow_spec_file(json_file, spec_directory):
        file_path = os.path.join(spec_directory, json_file)

        with open(file_path, 'r') as json_handle:
            data = json_handle.read()
            data_obj = json.loads(data)
            spec_file_name = '.'.join(json_file.name.split('.')[:-1])
            spec_file_path = os.path.join(spec_directory, spec_file_name)

            with open(spec_file_path, 'rb') as spec_handle:
                # workflow_spec_name = spec_directory.split('/')[-1]
                # workflow_spec = session.query(WorkflowSpecModel).filter(
                #     WorkflowSpecModel.display_name == workflow_spec_name).first()

                workflow_spec_file_model = session.query(FileModel).\
                    filter(FileModel.workflow_spec_id == data_obj['workflow_spec_id']).\
                    filter(FileModel.name == spec_file_name).\
                    first()
                if workflow_spec_file_model:
                    # update workflow_spec_file_model
                    FileService.update_file(workflow_spec_file_model, spec_handle.read(), CONTENT_TYPES[spec_file_name.split('.')[-1]])
                else:
                    # create new model
                    workflow_spec = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id==data_obj['workflow_spec_id']).first()
                    workflow_spec_file_model = FileService.add_workflow_spec_file(workflow_spec,
                                                                                  name=spec_file_name,
                                                                                  content_type=CONTENT_TYPES[spec_file_name.split('.')[-1]],
                                                                                  binary_data=spec_handle.read())

            print(f'process_workflow_spec_file: data_obj: {data_obj}')
        return workflow_spec_file_model

    @staticmethod
    def process_category(json_file, root):
        print(f'process_category: json_file: {json_file}')
        file_path = os.path.join(root, json_file)

        with open(file_path, 'r') as f_open:
            data = f_open.read()
            data_obj = json.loads(data)
            category = session.query(WorkflowSpecCategoryModel).filter(
                WorkflowSpecCategoryModel.display_name == data_obj['display_name']).first()
            if not category:
                category = WorkflowSpecCategoryModel(display_name=data_obj['display_name'],
                                                     display_order=data_obj['display_order'],
                                                     admin=data_obj['admin'])
                session.add(category)
            else:
                category.display_order = data_obj['display_order']
                category.admin = data_obj['admin']
            # print(data)
            print(f'process_category: category: {category}')

        session.commit()
        return category

    def process_workflow_spec_directory(self, spec_directory):
        print(f'process_workflow_spec_directory: {spec_directory}')
        files, directories = self.process_directory(spec_directory)

        for file in files:
            if file.name.endswith('.json'):
                file_model = self.process_workflow_spec_file(file, spec_directory)

        # TODO:
        #  If this is a migration, then we are backing out of the migration,
        #  so we need to add an entry to both file and file_data tables.
        #  If this is not a migration, and we are just loading from the filesystem,
        #  then we only need to add an entry to the file table (file_data won't exist)

    def process_category_directory(self, category_directory):
        print(f'process_category_directory: {category_directory}')
        files, directories = self.process_directory(category_directory)

        for file in files:
            if file.name.endswith('.json'):
                workflow_spec = self.process_workflow_spec(file, category_directory)

        for workflow_spec_directory in directories:
            directory_path = os.path.join(category_directory, workflow_spec_directory)
            self.process_workflow_spec_directory(directory_path)

    def process_root_directory(self, root_directory):

        files, directories = self.process_directory(root_directory)
        for file in files:
            if file.name.endswith('.json'):
                category_model = self.process_category(file, root_directory)
        WorkflowService.cleanup_workflow_spec_category_display_order()

        for directory in directories:
            directory_path = os.path.join(root_directory, directory)
            self.process_category_directory(directory_path)

    def update_file_metadata_from_filesystem(self, root_directory):
        self.process_root_directory(root_directory)


class ToFilesystemService(object):

    @staticmethod
    def process_category(location, category):
        # Make sure a directory exists for the category
        # Add a json file dumped from the category model
        category_path = os.path.join(location, category.display_name)
        os.makedirs(os.path.dirname(category_path), exist_ok=True)
        json_file_name = f'{category.display_name}.json'
        json_file_path = os.path.join(location, json_file_name)
        category_model_schema = WorkflowSpecCategoryModelSchema().dumps(category)
        with open(json_file_path, 'w') as j_handle:
            j_handle.write(category_model_schema)

    @staticmethod
    def process_workflow_spec(location, workflow_spec, category_name_string):
        # Make sure a directory exists for the workflow spec
        # Add a json file dumped from the workflow spec model
        workflow_spec_path = os.path.join(location, category_name_string, workflow_spec.display_name)
        os.makedirs(os.path.dirname(workflow_spec_path), exist_ok=True)
        json_file_name = f'{workflow_spec.display_name}.json'
        json_file_path = os.path.join(location, category_name_string, json_file_name)
        workflow_spec_schema = WorkflowSpecModelSchema().dumps(workflow_spec)
        with open(json_file_path, 'w') as j_handle:
            j_handle.write(workflow_spec_schema)

    @staticmethod
    def process_workflow_spec_file(session, workflow_spec_file, workflow_spec_file_path):
        # workflow_spec_file_path = os.path.join
        os.makedirs(os.path.dirname(workflow_spec_file_path), exist_ok=True)

        file_data_model = session.query(FileDataModel). \
            filter(FileDataModel.file_model_id == workflow_spec_file.id). \
            order_by(desc(FileDataModel.version)). \
            first()
        with open(workflow_spec_file_path, 'wb') as f_handle:
            f_handle.write(file_data_model.data)

        json_file_path = f'{workflow_spec_file_path}.json'
        workflow_spec_file_model = session.query(FileModel).filter(FileModel.id==file_data_model.file_model_id).first()
        workflow_spec_file_schema = FileModelSchema().dumps(workflow_spec_file_model)
        with open(json_file_path, 'w') as j_handle:
            j_handle.write(workflow_spec_file_schema)

    def write_file_to_system(self, session, file_model, location):

        category_name = None
        # location = SpecFileService.get_sync_file_root()

        if file_model.workflow_spec_id is not None:
            # we have a workflow spec file
            workflow_spec_model = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id == file_model.workflow_spec_id).first()
            if workflow_spec_model:

                if workflow_spec_model.category_id is not None:
                    category_model = session.query(WorkflowSpecCategoryModel).filter(WorkflowSpecCategoryModel.id == workflow_spec_model.category_id).first()
                    self.process_category(location, category_model)
                    category_name = category_model.display_name

                elif workflow_spec_model.is_master_spec:
                    category_name = 'Master Specification'

                elif workflow_spec_model.library:
                    category_name = 'Library Specs'

                elif workflow_spec_model.standalone:
                    category_name = 'Standalone'

            if category_name is not None:
                # Only process if we have a workflow_spec_model and category_name
                self.process_workflow_spec(location, workflow_spec_model, category_name)

                file_path = os.path.join(location,
                                         category_name,
                                         workflow_spec_model.display_name,
                                         file_model.name)
                self.process_workflow_spec_file(session, file_model, file_path)

        elif file_model.is_reference:
            # we have a reference file
            category_name = 'Reference'

            # self.process_workflow_spec(location, workflow_spec_model, category_name)

            file_path = os.path.join(location,
                                     category_name,
                                     file_model.name)

            self.process_workflow_spec_file(session, file_model, file_path)

        #     else:
        #         # We didn't get a workflow_spec_model
        #         pass
        #
        # elif file_model.workflow_id is not None:
        #     # we have a workflow file
        #     pass

        # elif file_model.is_reference:
        #     # we have a reference file?
        #     print(f'Reference file: {file_model.name}')
        #

        # else:
        #     print(f'Not processed: {file_model.name}')

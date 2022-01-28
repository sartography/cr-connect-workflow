import datetime
import os
from typing import List

from crc import app, session
from crc.api.common import ApiError
from crc.models.file import FileType, CONTENT_TYPES, File
from crc.models.workflow import WorkflowSpecModel, WorkflowLibraryModel

from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException

from lxml import etree


class SpecFileService(object):

    """We store spec files on the file system. This allows us to take advantage of Git for
       syncing and versioning.
        The files are stored in a directory whose path is determined by the category and spec names.
    """

    @staticmethod
    def get_files(workflow_spec, file_name=None, include_libraries=False) -> List[File]:
        """ Returns all files associated with a workflow specification """
        files = SpecFileService.__get_files(workflow_spec, file_name)
        if include_libraries:
            libraries = session.query(WorkflowLibraryModel).filter(
               WorkflowLibraryModel.workflow_spec_id == workflow_spec.id).all()
            for lib in libraries:
                files.extend(SpecFileService.__get_files(lib, file_name))
        return files

    @staticmethod
    def __get_files(workflow_spec: WorkflowSpecModel, file_name=None) -> List[File]:
        files = []
        items = os.scandir(SpecFileService.workflow_path(workflow_spec))
        for item in items:
            if item.is_file():
                if file_name is not None and item.name != file_name:
                    continue
                extension = SpecFileService.get_extension(item.name)
                file_type = FileType[extension]
                content_type = CONTENT_TYPES[file_type.name]
                stats = item.stat()
                file_size = stats.st_size
                last_modified = datetime.datetime.fromtimestamp(stats.st_mtime)
                files.append(File.spec_file(workflow_spec, item.name, file_type, content_type,
                                            last_modified, file_size))
        return files

    @staticmethod
    def add_file(workflow_spec: WorkflowSpecModel, file_name: str, binary_data: bytearray, content_type: str) -> File:
        # Same as update
        return SpecFileService.update_file(workflow_spec, file_name, binary_data, content_type)

    @staticmethod
    def update_file(workflow_spec: WorkflowSpecModel, file_name: str, binary_data, content_type) -> File:
        SpecFileService.assert_valid_file_name(file_name)
        file_path = SpecFileService.file_path(workflow_spec, file_name)
        SpecFileService.write_file_data_to_system(file_path, binary_data)
        extension = SpecFileService.get_extension(file_name)
        file_type = FileType[extension]
        last_modified = SpecFileService.__last_modified(file_path)
        size = os.path.getsize(file_path)
        file = File.spec_file(workflow_spec, file_name, file_type, content_type, last_modified, size)
        if file_name == workflow_spec.primary_file_name:
            SpecFileService.set_primary_bpmn(workflow_spec, file_name, binary_data)
        return file

    @staticmethod
    def set_primary_bpmn(workflow_spec: WorkflowSpecModel, file_name: str, binary_data=None):
        # If this is a BPMN, extract the process id, and determine if it is contains swim lanes.
        extension = SpecFileService.get_extension(file_name)
        file_type = FileType[extension]
        if file_type == FileType.bpmn:
            if not binary_data:
                binary_data = SpecFileService.get_data(workflow_spec, file_name)
            try:
                bpmn: etree.Element = etree.fromstring(binary_data)
                workflow_spec.primary_process_id = SpecFileService.get_process_id(bpmn)
                workflow_spec.primary_file_name = file_name
                workflow_spec.is_review = SpecFileService.has_swimlane(bpmn)
                session.add(workflow_spec)
                session.commit()
            except etree.XMLSyntaxError as xse:
                raise ApiError("invalid_xml", "Failed to parse xml: " + str(xse), file_name=file_name)
        else:
            raise ApiError("invalid_xml", "Only a BPMN can be the primary file.", file_name=file_name)

    @staticmethod
    def get_data(workflow_spec: WorkflowSpecModel, file_name: str):
        file_path = SpecFileService.file_path(workflow_spec, file_name)
        if not os.path.exists(file_path):
            raise ApiError("unknown_file", f"So file found with name {file_name} in {workflow_spec.display_name}")
        with open(file_path, 'rb') as f_handle:
            spec_file_data = f_handle.read()
        return spec_file_data

    #
    # Shared Methods
    #
    @staticmethod
    def root_path():
        dir_name = app.config['SYNC_FILE_ROOT']
        app_root = app.root_path
        return os.path.join(app_root, '..', dir_name)

    @staticmethod
    def category_name(spec: WorkflowSpecModel):
        if spec.is_master_spec:
            category_name = 'Master Specification'
        elif spec.library:
            category_name = 'Library Specs'
        elif spec.standalone:
            category_name = 'Standalone'
        else:
            category_name = spec.category.display_name
        return category_name

    @staticmethod
    def category_path(name: str):
        return os.path.join(SpecFileService.root_path(), name)

    @staticmethod
    def workflow_path(spec: WorkflowSpecModel):
        category_name = SpecFileService.category_name(spec)
        category_path = SpecFileService.category_path(category_name)
        return os.path.join(category_path, spec.display_name)

    @staticmethod
    def file_path(spec: WorkflowSpecModel, file_name: str):
        return os.path.join(SpecFileService.workflow_path(spec), file_name)

    @staticmethod
    def write_file_data_to_system(file_path, file_data):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f_handle:
            f_handle.write(file_data)

    @staticmethod
    def get_extension(file_name):
        basename, file_extension = os.path.splitext(file_name)
        return file_extension.lower().strip()[1:]

    @staticmethod
    def assert_valid_file_name(file_name):
        file_extension = SpecFileService.get_extension(file_name)
        if file_extension not in FileType._member_names_:
            raise ApiError('unknown_extension',
                           'The file you provided does not have an accepted extension:' +
                           file_extension, status_code=404)

    @staticmethod
    def has_swimlane(et_root: etree.Element):
        """
        Look through XML and determine if there are any lanes present that have a label.
        """
        elements = et_root.xpath('//bpmn:lane',
                                 namespaces={'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'})
        retval = False
        for el in elements:
            if el.get('name'):
                retval = True
        return retval

    @staticmethod
    def delete_file(spec, file_name):
        file_path = SpecFileService.file_path(spec, file_name)
        os.remove(file_path)

    @staticmethod
    def __last_modified(file_path: str):
        # Returns the last modified date of the given file.
        timestamp = os.path.getmtime(file_path)
        return datetime.datetime.fromtimestamp(timestamp)

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

import datetime
import os
import shutil
from typing import List

from crc import app, session
from crc.api.common import ApiError
from crc.models.file import FileType, CONTENT_TYPES, File

from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException

from lxml import etree

from crc.models.workflow import WorkflowSpecInfo
from crc.services.file_system_service import FileSystemService


class SpecFileService(FileSystemService):

    """We store spec files on the file system. This allows us to take advantage of Git for
       syncing and versioning.
        The files are stored in a directory whose path is determined by the category and spec names.
    """

    @staticmethod
    def get_files(workflow_spec: WorkflowSpecInfo, file_name=None, include_libraries=False) -> List[File]:
        """ Returns all files associated with a workflow specification """
        path = SpecFileService.workflow_path(workflow_spec)
        files = SpecFileService._get_files(path, file_name)
        if include_libraries:
            for lib_name in workflow_spec.libraries:
                lib_path = SpecFileService.library_path(lib_name)
                files.extend(SpecFileService._get_files(lib_path, file_name))
        return files

    @staticmethod
    def add_file(workflow_spec: WorkflowSpecInfo, file_name: str, binary_data: bytearray) -> File:
        # Same as update
        return SpecFileService.update_file(workflow_spec, file_name, binary_data)

    @staticmethod
    def update_file(workflow_spec: WorkflowSpecInfo, file_name: str, binary_data) -> File:
        SpecFileService.assert_valid_file_name(file_name)
        file_path = SpecFileService.file_path(workflow_spec, file_name)
        SpecFileService.write_file_data_to_system(file_path, binary_data)
        file = SpecFileService.to_file_object(file_name, file_path)
        if file_name == workflow_spec.primary_file_name:
            SpecFileService.set_primary_bpmn(workflow_spec, file_name, binary_data)
        elif workflow_spec.primary_file_name is None and file.type == FileType.bpmn:
            # If no primary process exists, make this pirmary process.
            SpecFileService.set_primary_bpmn(workflow_spec, file_name, binary_data)
        return file

    @staticmethod
    def get_data(workflow_spec: WorkflowSpecInfo, file_name: str):
        file_path = SpecFileService.file_path(workflow_spec, file_name)
        if not os.path.exists(file_path):
            # If the file isn't here, it may be in a library
            for lib in workflow_spec.libraries:
                lib_path = SpecFileService.library_path(lib)
                file_path = SpecFileService.file_path(workflow_spec, file_name)
                if os.path.exists(file_path):
                    break
        if not os.path.exists(file_path):
            raise ApiError("unknown_file", f"So file found with name {file_name} in {workflow_spec.display_name}")
        with open(file_path, 'rb') as f_handle:
            spec_file_data = f_handle.read()
        return spec_file_data

    @staticmethod
    def file_path(spec: WorkflowSpecInfo, file_name: str):
        return os.path.join(SpecFileService.workflow_path(spec), file_name)

    @staticmethod
    def last_modified(spec: WorkflowSpecInfo, file_name: str):
        path = SpecFileService.file_path(spec, file_name)
        return FileSystemService._last_modified(path)

    @staticmethod
    def delete_file(spec, file_name):
        # Fixme: Remember to remove the lookup files when the spec file is removed.
        # lookup_files = session.query(LookupFileModel).filter_by(file_model_id=file_id).all()
        # for lf in lookup_files:
        #     session.query(LookupDataModel).filter_by(lookup_file_model_id=lf.id).delete()
        #     session.query(LookupFileModel).filter_by(id=lf.id).delete()
        file_path = SpecFileService.file_path(spec, file_name)
        os.remove(file_path)

    @staticmethod
    def delete_all_files(spec):
        dir_path = SpecFileService.workflow_path(spec)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)

    @staticmethod
    def set_primary_bpmn(workflow_spec: WorkflowSpecInfo, file_name: str, binary_data=None):
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

            except etree.XMLSyntaxError as xse:
                raise ApiError("invalid_xml", "Failed to parse xml: " + str(xse), file_name=file_name)
        else:
            raise ApiError("invalid_xml", "Only a BPMN can be the primary file.", file_name=file_name)

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

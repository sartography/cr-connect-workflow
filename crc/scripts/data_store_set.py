from flask_bpmn.api.common import ApiError
from crc.scripts.script import Script
from crc.services.data_store_service import DataStoreBase
from crc.services.document_service import DocumentService
from crc.services.user_file_service import UserFileService

from flask import g


class DataStoreSet(Script):
    script_name = None
    data_store_args = None
    data_store_type = None
    data_store_file_id = None
    data_store_study_id = None
    data_store_user_id = None

    def set_args(self, study_id, **kwargs):
        self.validate_kw_args(**kwargs)
        self.data_store_args = [kwargs['key'], kwargs['value']]
        self.data_store_type = kwargs['type']
        if self.data_store_type == 'file':
            try:
                file_id = int(kwargs['file_id'])
            except Exception:
                raise ApiError("invalid_file_id",
                               f"The file_id must be an integer. You passed {kwargs['file_id']}.")
            self.script_name = 'file_data_set'
            self.data_store_file_id = file_id
            self.data_store_study_id = None
            self.data_store_user_id = None
        elif self.data_store_type == 'study':
            self.script_name = 'study_data_set'
            self.data_store_study_id = study_id
            self.data_store_file_id = None
            self.data_store_user_id = None
        elif self.data_store_type == 'user':
            self.script_name = 'user_data_set'
            self.data_store_user_id = g.user.uid
            self.data_store_file_id = None
            self.data_store_study_id = None

    def get_description(self):
        return """Sets a data store. Takes 3 mandatory keyword arguments; `type`, `key`, and `value`.
        Type is one of `file`, `study`, or `user`.
        Key and value are defined by the user.
        If type is `file`, then the script expects a fourth keyword argument of `file_id`."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.set_args(study_id, **kwargs)
        result = DataStoreBase().set_validate_common(task.id,
                                                   self.data_store_study_id,
                                                   workflow_id,
                                                   self.script_name,
                                                   self.data_store_user_id,
                                                   self.data_store_file_id,
                                                   *self.data_store_args)
        return result

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        self.set_args(study_id, **kwargs)

        if self.data_store_type == 'file' and self.data_store_args[0] == 'irb_code':
            irb_doc_code = kwargs['value']
            UserFileService.update_irb_code(self.data_store_file_id, irb_doc_code)

        return DataStoreBase().set_data_common(task.id,
                                             self.data_store_study_id,
                                             self.data_store_user_id,
                                             workflow_id,
                                             self.script_name,
                                             self.data_store_file_id,
                                             *self.data_store_args)

    @staticmethod
    def validate_kw_args(**kwargs):
        if 'type' not in kwargs or 'key' not in kwargs or 'value' not in kwargs:
            raise ApiError(code='missing_arguments',
                           message='The data_store_set script requires 3 keyword arguments; `type`, `key`, and `value`.')
        if kwargs['type'] == 'file' and 'file_id' not in kwargs:
            raise ApiError(code='missing_arguments',
                           message='If `type` is `file`, the data_store_set script requires a fourth keyword argument of `file_id`.')
        if kwargs['type'] == 'file' \
                and kwargs['key'] == 'irb_code' \
                and not DocumentService.is_allowed_document(kwargs.get('value')):
            raise ApiError(code="invalid_form_field_key",
                           message="When setting an irb_code, the value must be a valid document code. "
                           f"The value {kwargs.get('value')} is not a valid document code.")
        return True

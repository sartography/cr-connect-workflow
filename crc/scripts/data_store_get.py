from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.data_store_service import DataStoreBase

from flask import g


class ScriptTemplate(Script):
    data_store_type = None
    data_store_file_id = None
    data_store_study_id = None
    data_store_user_id = None
    data_store_key = None
    data_store_default = None

    def set_args(self, study_id, **kwargs):
        self.validate_kw_args(**kwargs)
        self.data_store_key = kwargs['key']
        if 'default' in kwargs.keys():
            self.data_store_default = kwargs['default']
        self.data_store_type = kwargs['type']
        if self.data_store_type == 'file':
            try:
                file_id = int(kwargs['file_id'])
            except Exception:
                raise ApiError("invalid_file_id",
                               f"The file_id must be an integer. You passed {kwargs['file_id']}.")
            self.data_store_file_id = file_id
            self.data_store_study_id = None
            self.data_store_user_id = None
        elif self.data_store_type == 'study':
            self.data_store_study_id = study_id
            self.data_store_file_id = None
            self.data_store_user_id = None
        elif self.data_store_type == 'user':
            self.data_store_user_id = g.user.uid
            self.data_store_file_id = None
            self.data_store_study_id = None

    def get_description(self):
        return """Returns a value from the data store. Requires 2 keyword arguments; `type` and `key`.
        Type is one of `file`, `study`, or `user`.
        Key is the key of the record you want returned.
        If type is `file`, then the script expects a third keyword argument of `file_id`."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.set_args(study_id, **kwargs)
        result = DataStoreBase().get_validate_common(self.data_store_type,
                                                     self.data_store_key,
                                                     self.data_store_study_id,
                                                     self.data_store_user_id,
                                                     self.data_store_file_id,
                                                     self.data_store_default)
        return result

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        self.set_args(study_id, **kwargs)
        result = DataStoreBase().get_data_common(self.data_store_type,
                                                 self.data_store_key,
                                                 self.data_store_study_id,
                                                 self.data_store_user_id,
                                                 self.data_store_file_id,
                                                 self.data_store_default)
        return result

    @staticmethod
    def validate_kw_args(**kwargs):
        if 'type' not in kwargs or 'key' not in kwargs:
            raise ApiError(code='missing_arguments',
                           message='The data_store_set script requires 2 keyword arguments; `type` and `key`.')
        if kwargs['type'] == 'file' and 'file_id' not in kwargs:
            raise ApiError(code='missing_arguments',
                           message='If type is `file`, ' +
                                   'the data_store_set script requires a third keyword argument of `file_id`.')
        return True

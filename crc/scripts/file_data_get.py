from crc.api.common import ApiError
from crc.services.data_store_service import DataStoreBase
from crc.scripts.script import Script


class FileDataGet(Script, DataStoreBase):
    def get_description(self):
        return """Gets user data from the data store - takes two keyword arguments arguments: 'file_id' and 'key' """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.validate_kw_args(**kwargs)
        my_args = [kwargs['key']]
        if 'default' in kwargs.keys():
            my_args.append(kwargs['default'])
        result = self.get_validate_common('file_data_get', None, None, kwargs['file_id'], *my_args)
        return result

    @staticmethod
    def validate_kw_args(**kwargs):
        if kwargs.get('key', None) is None:
            raise ApiError(code="missing_argument",
                           message=f"The 'file_data_get' script requires a keyword argument of 'key'")

        if kwargs.get('file_id', None) is None:
            raise ApiError(code="missing_argument",
                           message=f"The 'file_data_get' script requires a keyword argument of 'file_id'")
        return True

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        self.validate_kw_args(**kwargs)
        my_args = [kwargs['key']]
        if 'default' in kwargs.keys():
            my_args.append(kwargs['default'])

        return self.get_data_common(None,
                                    None,
                                    'file_data_get',
                                    kwargs['file_id'],
                                    *my_args)

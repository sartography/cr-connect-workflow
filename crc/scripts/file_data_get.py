from flask import g

from crc.api.common import ApiError
from crc.services.data_store_service import DataStoreBase
from crc.scripts.script import Script


class FileDataGet(Script, DataStoreBase):
    def get_description(self):
        return """Gets user data from the data store - takes only two keyword arguments arguments: 'file_id' and 'key' """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if self.validate_kw_args(**kwargs):
            myargs = [kwargs['key']]
        return True

    def validate_kw_args(self,**kwargs):
        if kwargs.get('key',None) is None:
            raise ApiError(code="missing_argument",
                            message=f"The 'file_data_get' script requires a keyword argument of 'key'")

        if kwargs.get('file_id',None) is None:
            raise ApiError(code="missing_argument",
                            message=f"The 'file_data_get' script requires a keyword argument of 'file_id'")
        return True


    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if self.validate_kw_args(**kwargs):
            myargs = [kwargs['key']]
        if 'default' in kwargs.keys():
            myargs.append(kwargs['default'])

        return self.get_data_common(None,
                                    None,
                                    'file_data_get',
                                    kwargs['file_id'],
                                    *myargs)

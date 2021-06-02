from flask import g

from crc.api.common import ApiError
from crc.services.data_store_service import DataStoreBase
from crc.scripts.script import Script


class FileDataSet(Script, DataStoreBase):
    def get_description(self):
        return """Sets data the data store - takes three keyword arguments arguments: 'file_id' and 'key' and 'value'"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if self.validate_kw_args(**kwargs):
            myargs = [kwargs['key'],kwargs['value']]
        fileid = kwargs['file_id']
        del(kwargs['file_id'])
        return True

    def validate_kw_args(self,**kwargs):
        if kwargs.get('key',None) is None:
            raise ApiError(code="missing_argument",
                            message=f"The 'file_data_get' script requires a keyword argument of 'key'")

        if kwargs.get('file_id',None) is None:
            raise ApiError(code="missing_argument",
                            message=f"The 'file_data_get' script requires a keyword argument of 'file_id'")
        if kwargs.get('value',None) is None:
            raise ApiError(code="missing_argument",
                            message=f"The 'file_data_get' script requires a keyword argument of 'value'")

        return True


    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if self.validate_kw_args(**kwargs):
            myargs = [kwargs['key'],kwargs['value']]
        fileid = kwargs['file_id']
        del(kwargs['file_id'])
        return self.set_data_common(task.id,
                                    None,
                                    None,
                                    workflow_id,
                                    None,
                                    'file_data_set',
                                    fileid,
                                    *myargs,
                                    **kwargs)


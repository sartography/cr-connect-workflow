from flask import g

from crc.api.common import ApiError
from crc.scripts.data_store_base import DataStoreBase
from crc.scripts.script import Script
from crc.services.file_service import FileService


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

        try:
            fileid = int(kwargs['file_id'])
        except:
            raise ApiError("invalid_file_id",
                           "Attempting to update DataStore for an invalid fileid '%s'" % kwargs['file_id'])

        del(kwargs['file_id'])
        if kwargs['key'] == 'irb_code':
            irb_doc_code = kwargs['value']
            FileService.update_irb_code(fileid,irb_doc_code)


        return self.set_data_common(task.id,
                                    None,
                                    None,
                                    workflow_id,
                                    None,
                                    'file_data_set',
                                    fileid,
                                    *myargs,
                                    **kwargs)


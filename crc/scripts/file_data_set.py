from crc.api.common import ApiError
from crc.services.data_store_service import DataStoreBase
from crc.scripts.script import Script
from crc.services.document_service import DocumentService
from crc.services.user_file_service import UserFileService


class FileDataSet(Script, DataStoreBase):
    def get_description(self):
        return """Sets data the data store - takes three keyword arguments arguments: 'file_id', 'key' and 'value'"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.validate_kw_args(**kwargs)
        my_args = [kwargs['key'], kwargs['value']]
        file_id = kwargs['file_id']
        result = self.set_validate_common(task.id,
                                          study_id,
                                          workflow_id,
                                          'file_data_set',
                                          None,
                                          file_id,
                                          *my_args)
        return result

    @staticmethod
    def validate_kw_args(**kwargs):
        if kwargs.get('key', None) is None:
            raise ApiError(code="missing_argument",
                           message=f"The 'file_data_get' script requires a keyword argument of 'key'")
        if kwargs.get('file_id', None) is None:
            raise ApiError(code="missing_argument",
                           message=f"The 'file_data_get' script requires a keyword argument of 'file_id'")
        if kwargs.get('value', None) is None:
            raise ApiError(code="missing_argument",
                           message=f"The 'file_data_get' script requires a keyword argument of 'value'")

        if kwargs['key'] == 'irb_code' and not DocumentService.is_allowed_document(kwargs.get('value')):
            raise ApiError("invalid_form_field_key",
                           "When setting an irb_code, the form field id must match a known document in the "
                           "irb_documents.xlsx reference file.  This code is not found in that file '%s'" %
                           kwargs.get('value'))

        return True

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        self.validate_kw_args(**kwargs)
        my_args = [kwargs['key'], kwargs['value']]

        try:
            fileid = int(kwargs['file_id'])
        except Exception:
            raise ApiError("invalid_file_id",
                           "Attempting to update DataStore for an invalid file_id '%s'" % kwargs['file_id'])

        del(kwargs['file_id'])
        if kwargs['key'] == 'irb_code':
            irb_doc_code = kwargs['value']
            UserFileService.update_irb_code(fileid, irb_doc_code)

        return self.set_data_common(task.id,
                                    None,
                                    None,
                                    workflow_id,
                                    None,
                                    'file_data_set',
                                    fileid,
                                    *my_args,
                                    **kwargs)

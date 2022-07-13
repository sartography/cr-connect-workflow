from crc import session
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.workflow import WorkflowModel

from flask import g
from sqlalchemy import desc


class DataStoreBase(object):

    def set_validate_common(
            self, ds_type, ds_key, ds_value, task_id, workflow_id, study_id=None, user_id=None, file_id=None
    ):
        self.check_args_set(ds_type, ds_key, file_id)
        if ds_type == 'study':
            record = {'task_id': task_id, 'study_id': study_id, 'workflow_id': workflow_id, ds_key: ds_value}
        elif ds_type == 'file':
            record = {'task_id': task_id, 'study_id': study_id, 'workflow_id': workflow_id, 'file_id': file_id, ds_key: ds_value}
        elif ds_type == 'user':
            record = {'task_id': task_id, 'study_id': study_id, 'workflow_id': workflow_id, 'user_id': user_id, ds_key: ds_value}
        g.validation_data_store.append(record)
        return record

    def get_validate_common(self, ds_type, ds_key, study_id=None, user_id=None, file_id=None, ds_default=None):
        # This method uses a temporary validation_data_store that is only available for the current validation request.
        # This allows us to set data_store values during validation that don't affect the real data_store.
        # For data_store `gets`, we first look in the temporary validation_data_store.
        # If we don't find an entry in validation_data_store, we look in the real data_store.
        if ds_type == 'study':
            # If it's in the validation data store, return it
            for record in g.validation_data_store:
                if 'study_id' in record and record['study_id'] == study_id and ds_key in record:
                    return record[ds_key]
            # If not in validation_data_store, look in the actual data_store
            return self.get_data_common('study', ds_key, study_id, user_id, file_id, ds_default)
        elif ds_type == 'file':
            for record in g.validation_data_store:
                if 'file_id' in record and record['file_id'] == file_id and ds_key in record:
                    return record[ds_key]
            return self.get_data_common('file', ds_key, study_id, user_id, file_id, ds_default)
        elif ds_type == 'user':
            for record in g.validation_data_store:
                if 'user_id' in record and record['user_id'] == user_id and ds_key in record:
                    return record[ds_key]
            return self.get_data_common('user', ds_key, study_id, user_id, file_id, ds_default)

    @staticmethod
    def check_args_set(ds_type, ds_key, file_id):
        if ds_type is None or ds_key is None:
            raise ApiError(code="missing_argument",
                           message="Setting a data store requires `type` and `key` keyword arguments")
        if ds_type not in ('study', 'user', 'file'):
            raise ApiError(code='bad_ds_type',
                           message=f"The data store service `type` must be `study`, `user`, or `file`. We received {ds_type}")
        if ds_type == 'file' and file_id is None:
            raise ApiError(code="missing_argument",
                           message="The file data store service requires a `file_id`.")

    @staticmethod
    def check_args_get(dstore_type, dstore_key, file_id):
        if dstore_type is None or dstore_key is None:
            raise ApiError(code="missing_argument",
                           message=f"The data store service requires a `type` and `key`")
        if dstore_type == 'file' and file_id is None:
            raise ApiError(code="missing_argument",
                           message="The file data store service requires a `file_id`.")

    def set_data_common(
            self, ds_type, ds_key, ds_value, task_spec, study_id, user_id, workflow_id, file_id
    ):
        self.check_args_set(ds_type, ds_key, file_id)

        if ds_value == '' or ds_value is None:
            # We delete the data store if the value is empty
            return self.delete_data_store(study_id, user_id, file_id, ds_key)
        workflow_spec_id = None
        if workflow_id is not None:
            workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            workflow_spec_id = workflow.workflow_spec_id

        result = self.get_previous_data_store(ds_key, study_id, user_id, file_id)
        if result:
            dsm = result[0]
            dsm.value = ds_value
            if task_spec:
                dsm.task_spec = task_spec
            if workflow_id:
                dsm.workflow_id = workflow_id
            if workflow_spec_id:
                dsm.spec_id = workflow_spec_id
            if len(result) > 1:
                # We had a bug where we had created new records instead of updating values of existing records
                # This just gets rid of all the old unused records
                self.delete_extra_data_stores(result[1:])
        else:
            dsm = DataStoreModel(key=ds_key,
                                 value=ds_value,
                                 study_id=study_id,
                                 task_spec=task_spec,
                                 user_id=user_id,  # Make this available to any User
                                 file_id=file_id,
                                 workflow_id=workflow_id,
                                 spec_id=workflow_spec_id)
        session.add(dsm)
        session.commit()

        return dsm.value

    def get_data_common(self, dstore_type, dstore_key, study_id, user_id, file_id=None, dstore_default=None):
        self.check_args_get(dstore_type, dstore_key, file_id)
        record = session.query(DataStoreModel).\
            filter_by(study_id=study_id,
                      user_id=user_id,
                      file_id=file_id,
                      key=dstore_key).\
            first()
        if record is not None:
            return record.value
        else:
            # This is a possible default value passed in from the data_store get methods
            if dstore_default is not None:
                return dstore_default

    @staticmethod
    def get_multi_common(study_id, user_id, file_id=None):
        results = session.query(DataStoreModel).filter_by(study_id=study_id,
                                                          user_id=user_id,
                                                          file_id=file_id)
        return results

    def delete_data_store(self, study_id, user_id, file_id, ds_key):
        records = self.get_previous_data_store(ds_key, study_id, user_id, file_id)
        if records is not None:
            for record in records:
                session.delete(record)
            session.commit()

    @staticmethod
    def delete_extra_data_stores(records):
        """We had a bug where we created new records instead of updating existing records.
           We use this to clean up all the extra records.
           We may remove this method in the future."""
        for record in records:
            session.query(DataStoreModel).filter(DataStoreModel.id == record.id).delete()
        session.commit()

    @staticmethod
    def get_previous_data_store(ds_key, study_id, user_id, file_id):
        query = session.query(DataStoreModel).filter(DataStoreModel.key == ds_key)
        if study_id:
            query = query.filter(DataStoreModel.study_id == study_id)
        elif file_id:
            query = query.filter(DataStoreModel.file_id == file_id)
        elif user_id:
            query = query.filter(DataStoreModel.user_id == user_id)
        result = query.order_by(desc(DataStoreModel.last_updated)).all()
        return result

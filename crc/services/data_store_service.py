from crc import session
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.workflow import WorkflowModel

from flask import g


class DataStoreBase(object):

    def set_validate_common(self, task_id, study_id, workflow_id, script_name, user_id, file_id, *args):
        self.check_args_2(args, script_name)
        if script_name == 'study_data_set':
            record = {'task_id': task_id, 'study_id': study_id, 'workflow_id': workflow_id, args[0]: args[1]}
        elif script_name == 'file_data_set':
            record = {'task_id': task_id, 'study_id': study_id, 'workflow_id': workflow_id, 'file_id': file_id, args[0]: args[1]}
        elif script_name == 'user_data_set':
            record = {'task_id': task_id, 'study_id': study_id, 'workflow_id': workflow_id, 'user_id': user_id, args[0]: args[1]}
        g.validation_data_store.append(record)
        return record

    def get_validate_common(self, script_name, study_id=None, user_id=None, file_id=None, *args):
        # This method uses a temporary validation_data_store that is only available for the current validation request.
        # This allows us to set data_store values during validation that don't affect the real data_store.
        # For data_store `gets`, we first look in the temporary validation_data_store.
        # If we don't find an entry in validation_data_store, we look in the real data_store.
        if script_name == 'study_data_get':
            # If it's in the validation data store, return it
            for record in g.validation_data_store:
                if 'study_id' in record and record['study_id'] == study_id and args[0] in record:
                    return record[args[0]]
            # If not in validation_data_store, look for in the actual data_store
            return self.get_data_common(study_id, user_id, 'study_data_get', file_id, *args)
        elif script_name == 'file_data_get':
            for record in g.validation_data_store:
                if 'file_id' in record and record['file_id'] == file_id and args[0] in record:
                    return record[args[0]]
            return self.get_data_common(study_id, user_id, 'file_data_get', file_id, *args)
        elif script_name == 'user_data_get':
            for record in g.validation_data_store:
                if 'user_id' in record and record['user_id'] == user_id and args[0] in record:
                    return record[args[0]]
            return self.get_data_common(study_id, user_id, 'user_data_get', file_id, *args)

    @staticmethod
    def check_args(args, maxlen=1, script_name='study_data_get'):
        if len(args) < 1 or len(args) > maxlen:
            raise ApiError(code="missing_argument",
                           message=f"The {script_name} script takes either one or two arguments, "
                                   f"starting with the key and an optional default")

    @staticmethod
    def check_args_2(args, script_name='study_data_set'):
        if len(args) != 2:
            raise ApiError(code="missing_argument",
                           message=f"The {script_name} script takes two arguments, key and value, in that order.")

    def set_data_common(self,
                        task_spec,
                        study_id,
                        user_id,
                        workflow_id,
                        workflow_spec_id,
                        script_name,
                        file_id,
                        *args,
                        **kwargs):

        self.check_args_2(args, script_name=script_name)
        if workflow_spec_id is None and workflow_id is not None:
            workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            workflow_spec_id = workflow.workflow_spec_id
        dsm = DataStoreModel(key=args[0],
                             value=args[1],
                             study_id=study_id,
                             task_spec=task_spec,
                             user_id=user_id,  # Make this available to any User
                             file_id=file_id,
                             workflow_id=workflow_id,
                             spec_id=workflow_spec_id)
        session.add(dsm)
        session.commit()

        return dsm.value

    def get_data_common(self, study_id, user_id, script_name, file_id=None, *args):
        self.check_args(args, 2, script_name)
        record = session.query(DataStoreModel).filter_by(study_id=study_id,
                                                         user_id=user_id,
                                                         file_id=file_id,
                                                         key=args[0]).first()
        if record:
            return record.value
        else:
            # This is a possible default value passed in from the data_store get methods
            if len(args) == 2:
                return args[1]

    @staticmethod
    def get_multi_common(study_id, user_id, file_id=None):
        results = session.query(DataStoreModel).filter_by(study_id=study_id,
                                                          user_id=user_id,
                                                          file_id=file_id)
        return results

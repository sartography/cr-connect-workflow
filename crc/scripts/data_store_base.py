import importlib
import os
import pkgutil
from crc import session
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.workflow import WorkflowModel
from datetime import datetime


class DataStoreBase(object):

    def overwritten(self, value, prev_value):
        if prev_value is None:
            overwritten = False
        else:
            if prev_value == value:
                overwritten = False
            else:
                overwritten = True
        return overwritten


    def set_validate_common(self, study_id, workflow_id, user_id, script_name, file_id, *args):
        self.check_args_2(args, script_name)
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        self.get_prev_value(study_id=study_id, user_id=user_id, file_id=file_id, key=args[0])

    def check_args(self, args, maxlen=1, script_name='study_data_get'):
        if len(args) < 1 or len(args) > maxlen:
            raise ApiError(code="missing_argument",
                           message=f"The {script_name} script takes either one or two arguments, "
                                   f"starting with the key and an optional default")

    def check_args_2(self, args, script_name='study_data_set'):
        if len(args) != 2:
            raise ApiError(code="missing_argument",
                           message=f"The {script_name} script takes two arguments, starting with the key and a " 
                                   "value for the key")

    def get_prev_value(self, study_id, user_id, key, file_id):
        study = session.query(DataStoreModel).filter_by(study_id=study_id,
                                                        user_id=user_id,
                                                        file_id=file_id,
                                                        key=key).first()
        return study

    def set_data_common(self,
                        task_id,
                        study_id,
                        user_id,
                        workflow_id,
                        workflow_spec_id,
                        script_name,
                        file_id,
                        *args,
                        **kwargs):

        self.check_args_2(args, script_name=script_name)
        study = self.get_prev_value(study_id=study_id,
                                    user_id=user_id,
                                    file_id=file_id,
                                    key=args[0])
        if workflow_spec_id is None and workflow_id is not None:
            workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            workflow_spec_id = workflow.workflow_spec_id
        if study is not None:
            prev_value = study.value
        else:
            prev_value = None
            study = DataStoreModel(key=args[0], value=args[1],
                                   study_id=study_id,
                                   task_id=task_id,
                                   user_id=user_id,  # Make this available to any User
                                   file_id=file_id,
                                   workflow_id=workflow_id,
                                   spec_id=workflow_spec_id)
        study.value = args[1]
        study.last_updated = datetime.utcnow()
        overwritten = self.overwritten(study.value, prev_value)
        session.add(study)
        session.commit()
        return {'new_value': study.value,
                'old_value': prev_value,
                'overwritten': overwritten}

    def get_data_common(self, study_id, user_id, script_name, file_id=None, *args):
        self.check_args(args, 2, script_name)
        study = session.query(DataStoreModel).filter_by(study_id=study_id,
                                                        user_id=user_id,
                                                        file_id=file_id,
                                                        key=args[
            0]).first()
        if study:
            return study.value
        else:
            return args[1]

    def get_multi_common(self, study_id, user_id, file_id=None):
        study = session.query(DataStoreModel).filter_by(study_id=study_id,
                                                        user_id=user_id,
                                                        file_id=file_id)
        return study

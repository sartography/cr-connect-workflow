import requests

from crc.scripts.script import Script, DataStoreBase
from crc import session
from crc.models.workflow import WorkflowModel
from crc.models.data_store import DataStoreModel

class StudyDataSet(Script,DataStoreBase):
    def get_description(self):
        return """Sets study data from the data store."""


    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.check_args(args)
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        self.get_prev_value(study_id,args[0])


    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        self.check_args(args)
        study = self.get_prev_value(study_id,args[0])
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        if study is not None:
            prev_value = study.key
        else:
            prev_value = None
            study = DataStoreModel(key=args[0],value=args[1],
                                   study_id=study_id,
                                   task_id=task.id,
                                   user_id=None,             # Make this available to any User
                                   workflow_id= workflow_id,
                                   spec_id=workflow.workflow_spec_id)

        overwritten = self.overwritten(study.value,prev_value)
        session.add(study)
        return (study.value, prev_value, overwritten)


    def get_prev_value(self,study_id,key):
        study = session.query(DataStoreModel).filter_by(study_id=study_id,user_id=None,key=key).first()
        return study


    def check_args(self, args):
        if len(args) != 2:
            raise ApiError(code="missing_argument",
            message="The study_data_set script takes two arguments, starting with the key and a " +\
                    "value for the key")

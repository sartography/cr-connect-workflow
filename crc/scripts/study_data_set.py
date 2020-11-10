import requests

from crc.scripts.script import Script, DataStoreBase
from crc import session
from crc.models.workflow import WorkflowModel
from crc.models.data_store import DataStoreModel

class StudyDataSet(Script,DataStoreBase):
    def get_description(self):
        return """Sets study data from the data store."""


    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.set_validate_common(study_id,
                                 workflow_id,
                                 None,
                                 'study_data_set',
                                 *args)


    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return self.set_data_common(task,
                                    study_id,
                                    None,
                                    workflow_id,
                                    'study_data_set',
                                    *args,
                                    **kwargs)







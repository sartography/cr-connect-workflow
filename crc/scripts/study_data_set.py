from crc.services.data_store_service import DataStoreBase
from crc.scripts.script import Script


class StudyDataSet(Script, DataStoreBase):
    def get_description(self):
        return """Sets study data from the data store. Takes two positional arguments key and value"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        result = self.set_validate_common(task.id,
                                          study_id,
                                          workflow_id,
                                          'study_data_set',
                                          None,
                                          None,
                                          *args)
        return result

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return self.set_data_common(task.id,
                                    study_id,
                                    None,
                                    workflow_id,
                                    None,
                                    'study_data_set',
                                    None,
                                    *args,
                                    **kwargs)

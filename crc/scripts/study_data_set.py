from crc.scripts.data_store_base import DataStoreBase
from crc.scripts.script import Script


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
        return self.set_data_common(task.id,
                                    study_id,
                                    None,
                                    workflow_id,
                                    None,
                                    'study_data_set',
                                    *args,
                                    **kwargs)







from crc.services.data_store_service import DataStoreBase
from crc.scripts.script import Script


class StudyDataGet(Script,DataStoreBase):
    def get_description(self):
        return """Gets study data from the data store."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return self.get_data_common(study_id,
                                    None,
                                    'study_data_get',
                                    None,
                                    *args)


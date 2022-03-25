from flask import g

from crc.services.data_store_service import DataStoreBase
from crc.scripts.script import Script


class UserDataSet(Script, DataStoreBase):
    def get_description(self):
        return """Sets user data to the data store these are positional arguments key and value.
        example: user_data_set('my_key','my_value')
        """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.set_validate_common(task.id,
                                 study_id,
                                 workflow_id,
                                 'user_data_set',
                                 g.user.uid,
                                 None,
                                 *args)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return self.set_data_common(task.id,
                                    None,
                                    g.user.uid,
                                    workflow_id,
                                    None,
                                    'user_data_set',
                                    None,
                                    *args,
                                    **kwargs)

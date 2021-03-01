from flask import g

from crc.scripts.data_store_base import DataStoreBase
from crc.scripts.script import Script


class UserDataSet(Script,DataStoreBase):
    def get_description(self):
        return """Sets user data to the data store these are positional arguments key and value.
        example: user_data_set('mykey','myvalue')
        """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.set_validate_common(None,
                                 workflow_id,
                                 g.user.uid,
                                 'user_data_set',
                                 *args)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return self.set_data_common(task.id,
                                    None,
                                    g.user.uid,
                                    workflow_id,
                                    None,
                                    'user_data_set',
                                    *args,
                                    **kwargs)




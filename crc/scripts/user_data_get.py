import requests

from crc.scripts.script import Script, DataStoreBase
from crc import session
from crc.models.data_store import DataStoreModel
from flask import g

class UserDataGet(Script,DataStoreBase):
    def get_description(self):
        return """Gets user data from the data store."""


    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return self.get_data_common(None,
                                    g.user.uid,
                                    'user_data_get',
                                    *args)

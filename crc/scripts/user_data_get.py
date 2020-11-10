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
        self.check_args(args,2)
        study = session.query(DataStoreModel).filter_by(study_id=None,user_id=g.user.uid,key=args[0]).first()
        if study:
            return study.value
        else:
            return args[1]

    def check_args(self, args, maxlen=1):
        if len(args) < 1 or len(args) > maxlen :
            raise ApiError(code="missing_argument",
            message="The study_data_get script takes either one or two arguments, starting with the key and an " + \
                    "optional default")

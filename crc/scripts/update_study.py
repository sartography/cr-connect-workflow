import requests

from crc import db
from crc.api.common import ApiError
from crc.models.study import StudyModel
from crc.scripts.script import Script


class mock_study:
    def __init__(self):
        self.title = ""
        self.principle_investigator_id = ""


class UpdateStudy(Script):

    argument_error_message = "You must supply at least one argument to the " \
                             "update_study task, in the form [study_field]=[value]",

    def get_description(self):
        return """Allows you to set specific attributes on the Study model by mapping them to 
values in the task data.  Should be called with the value to set (either title, short_title, or pi)

Example:
update_study(title=PIComputingID.label, short_title="Really Short Name")
"""
    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        study = mock_study
        self.__update_study(task, study, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        study = db.session.query(StudyModel).filter(StudyModel.id == study_id).first()
        self.__update_study(task, study, *args, **kwargs)
        db.session.add(study)

    def __update_study(self, task, study, *args, **kwargs):
        if len(kwargs.keys()) < 1:
            raise ApiError.from_task("missing_argument", self.argument_error_message,
                                     task=task)

        for arg in kwargs.keys():
            if arg.lower() == "title":
                study.title = kwargs[arg]
            elif arg.lower() == "short_title":
                study.short_title = kwargs[arg]
            elif arg.lower() == "pi":
                study.primary_investigator_id = kwargs[arg]
            else:
                raise ApiError.from_task("invalid_argument", self.argument_error_message,
                                         task=task)

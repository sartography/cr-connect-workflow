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
                             "update_study task, in the form [study_field]:[value]",

    def get_description(self):
        return """
Allows you to set specific attributes on the Study model by mapping them to 
values in the task data.  Should be called with the value to set (either title, or pi)
followed by a ":" and then the value to use in dot notation.

Example:
UpdateStudy title:PIComputingID.label pi:PIComputingID.value
"""
    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        study = mock_study
        self.__update_study(task, study, *args)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        study = db.session.query(StudyModel).filter(StudyModel.id == study_id).first()
        self.__update_study(task, study, *args)
        db.session.add(study)

    def __update_study(self, task, study, *args):
        if len(args) < 1:
            raise ApiError.from_task("missing_argument", self.argument_error_message,
                                     task=task)

        for arg in args:
            try:
                field, value_lookup = arg.split(':')
            except:
                raise ApiError.from_task("invalid_argument", self.argument_error_message,
                                         task=task)

            value = task.workflow.script_engine.evaluate_expression(task, value_lookup)

            if field.lower() == "title":
                study.title = value
            elif field.lower() == "pi":
                study.primary_investigator_id = value
            else:
                raise ApiError.from_task("invalid_argument", self.argument_error_message,
                                         task=task)

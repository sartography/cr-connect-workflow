from crc import db, session
from crc.api.common import ApiError
from crc.models.study import StudyModel
from crc.scripts.script import Script
from crc.services.study_service import StudyService


class GetCurrentBCA(Script):

    @staticmethod
    def __get_study_title(study_id):
        """Return the study title for the given study ID."""
        study = session.query(StudyModel).filter(StudyModel.id == study_id).first()
        if study:
            return study.title
        return study_id

    @staticmethod
    def get_study_url(study_id):
        return StudyService.get_study_url(study_id)

    def get_description(self):
        return """This is my description"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        current_bca = []
        statement = """SELECT DISTINCT ON (study_id) study_id, date
FROM task_event
WHERE task_name = 'Do_Upload_BCA_Send_Approver_Request'
  and action = 'ASSIGNMENT'
  and task_state = 'READY'
GROUP BY study_id, date;
"""

        task_event_results = db.session.execute(statement)
        if task_event_results:
            for task_event in task_event_results:
                returned_values = {
                    'study_id': task_event[0],
                    'study_title': self.__get_study_title(task_event[0]),
                    'study_url': self.get_study_url(task_event[0]),
                    'date': task_event[1]
                }
                current_bca.append(returned_values)
                print(task_event)

        print('here')
        return current_bca

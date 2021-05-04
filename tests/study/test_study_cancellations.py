from tests.base_test import BaseTest

from crc import session
from crc.models.study import StudyModel, StudySchema
from crc.models.workflow import WorkflowModel, WorkflowSpecModel

import json


class TestStudyCancellations(BaseTest):

    def update_study_status(self, study, study_schema):
        put_response = self.app.put('/v1.0/study/%i' % study.id,
                                    content_type="application/json",
                                    headers=self.logged_in_headers(),
                                    data=json.dumps(study_schema))
        self.assert_success(put_response)

        # The error happened when the dashboard reloaded,
        # in particular, when we got the studies for the user
        api_response = self.app.get('/v1.0/study', headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)

        study_result = session.query(StudyModel).filter(StudyModel.id == study.id).first()
        return study_result

    def put_study_on_hold(self, study_id):
        study = session.query(StudyModel).filter_by(id=study_id).first()

        study_schema = StudySchema().dump(study)
        study_schema['status'] = 'hold'
        study_schema['comment'] = 'This is my hold comment'

        self.update_study_status(study, study_schema)

        study_result = session.query(StudyModel).filter(StudyModel.id == study_id).first()
        return study_result

    def load_workflow(self):
        self.load_example_data()
        workflow = self.create_workflow('study_cancellations')
        study_id = workflow.study_id
        return workflow, study_id

    def get_first_task(self, workflow):
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.assertEqual('Activity_Hello', first_task.name)
        return workflow_api, first_task

    def get_second_task(self, workflow):
        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('Activity_HowMany', second_task.name)
        return workflow_api, second_task

    def get_third_task(self, workflow):
        workflow_api = self.get_workflow_api(workflow)
        third_task = workflow_api.next_task
        self.assertEqual('Activity_Modify', third_task.name)
        return workflow_api, third_task

    def test_before_cancel(self):

        workflow, study_id = self.load_workflow()
        self.get_first_task(workflow)

        study_result = self.put_study_on_hold(study_id)
        self.assertEqual('Beer consumption in the bipedal software engineer', study_result.title)

    def test_first_cancel(self):
        workflow, study_id = self.load_workflow()
        workflow_api, first_task = self.get_first_task(workflow)

        self.complete_form(workflow, first_task, {})

        study_result = self.put_study_on_hold(study_id)
        self.assertEqual('New Title', study_result.title)

    def test_second_cancel(self):

        workflow, study_id = self.load_workflow()
        workflow_api, first_task = self.get_first_task(workflow)

        self.complete_form(workflow, first_task, {})

        workflow_api, next_task = self.get_second_task(workflow)
        self.complete_form(workflow, next_task, {'how_many': 3})

        study_result = self.put_study_on_hold(study_id)
        self.assertEqual('Second Title', study_result.title)

    def test_after_cancel(self):

        workflow, study_id = self.load_workflow()
        workflow_api, first_task = self.get_first_task(workflow)

        self.complete_form(workflow, first_task, {})

        workflow_api, second_task = self.get_second_task(workflow)
        self.complete_form(workflow, second_task, {'how_many': 3})

        workflow_api, third_task = self.get_third_task(workflow)
        self.complete_form(workflow, third_task, {})

        study_result = self.put_study_on_hold(study_id)
        self.assertEqual('Beer consumption in the bipedal software engineer', study_result.title)

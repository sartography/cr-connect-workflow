from tests.base_test import BaseTest
from crc.scripts.study_info import StudyInfo
from crc import app
from unittest.mock import patch


class TestStudyInfoScript(BaseTest):

    def do_work(self, info_type):
        app.config['PB_ENABLED'] = True
        self.load_example_data()
        workflow = self.create_workflow('study_info_script')
        workflow_api = self.get_workflow_api(workflow)
        # grab study_info directly from script
        study_info = StudyInfo().do_task(workflow_api.study_id, workflow.study.id, workflow.id, info_type)

        # grab study info through a workflow
        first_task = workflow_api.next_task
        self.complete_form(workflow, first_task, {'which': info_type})
        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task

        return study_info, second_task

    def test_info_script_info(self):
        study_info, second_task = self.do_work(info_type='info')

        self.assertEqual(study_info['title'], second_task.data['info']['title'])
        self.assertEqual(study_info['primary_investigator_id'], second_task.data['info']['primary_investigator_id'])
        self.assertIn(study_info['title'], second_task.documentation)

    def test_info_script_investigators(self):
        # We don't have a test for this yet
        # I believe we just need to set up some test data.
        # study_info, second_task = self.do_work(info_type='investigators')
        # if study_info:
        #     # TODO: add investigators with user_ids that are not None
        pass

    def test_info_script_roles(self):
        study_info, second_task = self.do_work(info_type='roles')
        self.assertEqual(study_info, second_task.data['info'])

    # @patch('crc.services.protocol_builder.requests.get')
    def test_info_script_details(self):
        # TODO: Set up test PB data
        # study_info, second_task = self.do_work(info_type='details')
        pass

    def test_info_script_documents(self):
        study_info, second_task = self.do_work(info_type='documents')
        self.assertEqual(study_info, second_task.data['info'])

    def test_info_script_sponsors(self):
        # TODO: Set up test PB data
        # study_info, second_task = self.do_work(info_type='sponsors')
        pass

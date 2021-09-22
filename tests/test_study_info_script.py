from tests.base_test import BaseTest
from crc.scripts.study_info import StudyInfo
from crc import app
from unittest.mock import patch
from crc.services.protocol_builder import ProtocolBuilderService


class TestStudyInfoScript(BaseTest):

    test_uid = "dhf8r"
    test_study_id = 1

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

    def test_info_script_updated_study_info(self):
        self.load_example_data()
        short_name = "My Short Name"
        proposal_name = "My Proposal Name"
        workflow = self.create_workflow('update_study_info')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.complete_form(workflow, task, {'short_name': short_name, 'proposal_name': proposal_name})
        task = workflow_api.next_task
        # The workflow calls study_info('info') and puts the result in Element Documentation
        # I create a dictionary of that info with `eval` to make the asserts easier to read
        study_info = eval(task.documentation)

        self.assertIn('short_name', study_info.keys())
        self.assertEqual(short_name, study_info['short_name'])
        self.assertIn('proposal_name', study_info.keys())
        self.assertIn(proposal_name, study_info['proposal_name'])

    @patch('crc.services.protocol_builder.requests.get')
    def test_info_script_investigators(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('investigators.json')
        response = ProtocolBuilderService.get_investigators(self.test_study_id)
        study_info, second_task = self.do_work(info_type='investigators')
        for i in range(len(response)):
            r = response[i]
            s = second_task.data['info'][response[i]['INVESTIGATORTYPE']]
            self.assertEqual(r['INVESTIGATORTYPEFULL'], s['label'])

    # def test_info_script_roles(self):
    #     study_info, second_task = self.do_work(info_type='roles')
    #     self.assertEqual(study_info, second_task.data['info'])

    @patch('crc.services.protocol_builder.requests.get')
    def test_info_script_details(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('study_details.json')
        response = ProtocolBuilderService.get_study_details(self.test_study_id)
        study_info, second_task = self.do_work(info_type='details')
        self.assertEqual(response['IBC_NUMBER'], second_task.data['info']['IBC_NUMBER'])
        self.assertEqual(response['IDE'], second_task.data['info']['IDE'])
        self.assertEqual(response['IND_1'], second_task.data['info']['IND_1'])
        self.assertEqual(response['IND_2'], second_task.data['info']['IND_2'])
        self.assertEqual(response['IND_3'], second_task.data['info']['IND_3'])

    # def test_info_script_documents(self):
    #     study_info, second_task = self.do_work(info_type='documents')
    #     self.assertEqual(study_info, second_task.data['info'])

    @patch('crc.services.protocol_builder.requests.get')
    def test_info_script_sponsors(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        response = ProtocolBuilderService.get_sponsors(self.test_study_id)
        study_info, second_task = self.do_work(info_type='sponsors')
        for i in range(len(response)):
            self.assertEqual(response[i]['SPONSOR_ID'], second_task.data['info'][i]['SPONSOR_ID'])
            self.assertEqual(response[i]['SP_NAME'], second_task.data['info'][i]['SP_NAME'])
            self.assertEqual(response[i]['SS_STUDY'], second_task.data['info'][i]['SS_STUDY'])

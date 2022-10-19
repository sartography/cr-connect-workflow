import io
import json

from tests.base_test import BaseTest
from crc.scripts.study_info import StudyInfo
from crc import app
from unittest.mock import patch
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.study_service import StudyService


class TestStudyInfoScript(BaseTest):

    test_uid = "dhf8r"
    test_study_id = 1

    def do_work(self, info_type):
        app.config['PB_ENABLED'] = True
        self.create_reference_document()
        self.workflow = self.create_workflow('study_info_script')
        self.workflow_api = self.get_workflow_api(self.workflow)
        # grab study_info directly from script
        study_info = StudyInfo().do_task(self.workflow_api.study_id, self.workflow.study.id, self.workflow.id, info_type)

        # grab study info through a workflow
        first_task = self.workflow_api.next_task
        self.complete_form(self.workflow, first_task, {'which': info_type})
        workflow_api = self.get_workflow_api(self.workflow)
        second_task = workflow_api.next_task

        return study_info, second_task

    def test_info_script_info(self):
        study_info, second_task = self.do_work(info_type='info')

        self.assertEqual(study_info['title'], second_task.data['info']['title'])
        self.assertIn(study_info['title'], second_task.documentation)

    def test_info_script_updated_study_info(self):

        short_name = "My Short Name"
        proposal_name = "My Proposal Name"
        workflow = self.create_workflow('update_study_info')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.complete_form(workflow, task, {'short_name': short_name, 'proposal_name': proposal_name})
        task = workflow_api.next_task
        study_info = task.data['my_study_info']
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
        response = ProtocolBuilderService.get_study_details(self.test_study_id)[0]
        study_info, second_task = self.do_work(info_type='details')
        self.assertEqual(response['IBC_NUMBER'], second_task.data['info']['IBC_NUMBER'])
        self.assertEqual(response['IDE'], second_task.data['info']['IDE'])
        self.assertEqual(response['IND_1'], second_task.data['info']['IND_1'])
        self.assertEqual(response['IND_2'], second_task.data['info']['IND_2'])
        self.assertEqual(response['IND_3'], second_task.data['info']['IND_3'])

    @patch('crc.services.protocol_builder.requests.get')
    def test_info_script_documents(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
        response = ProtocolBuilderService.get_required_docs(self.test_study_id)
        study_info, second_task = self.do_work(info_type='documents')
        self.assertEqual(study_info, second_task.data['info'])
        self.assertEqual(0, len(study_info['Grant_App']['files']), "Grant_App has not files yet.")
        # Add a grant app file
        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&irb_doc_code=%s' %
                           (self.workflow.study_id, self.workflow.id, second_task.name, 'Grant_App'), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_data = json.loads(rv.get_data(as_text=True))
        study_info = StudyService.get_documents_status(self.workflow.study_id, force=True)
        self.assertEqual(1, len(study_info['Grant_App']['files']), "Grant_App has exactly one file.")

        # Now get the study info again.
        study_info = StudyInfo().do_task(self.workflow_api.study_id, self.workflow.study.id, self.workflow.id,
                                         'documents')
        # The data should contain a file.
        self.assertEqual(1, len(study_info['Grant_App']['files']), "Grant_App has exactly one file.")

        # This file data returned should be the same as what we get back about the file when we uploaded it,
        # but the details on the document should be removed, because that would be recursive.
        del file_data['document']
        self.assertEqual(file_data, study_info['Grant_App']['files'][0])


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

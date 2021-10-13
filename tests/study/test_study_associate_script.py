from tests.base_test import BaseTest
import json
from unittest.mock import patch
import flask

from crc.api.common import ApiError
from crc.services.user_service import UserService

from crc import session, app
from crc.models.study import StudyModel
from crc.models.ldap import LdapSchema
from crc.services.ldap_service import LdapService
from crc.models.user import UserModel
from crc.api.study import user_studies
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService

class TestSudySponsorsScript(BaseTest):
    test_uid = "dhf8r"
    test_study_id = 1


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script_validation(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        flask.g.user = UserModel(uid='dhf8r')
        self.load_example_data() # study_info script complains if irb_documents.xls is not loaded
                                 # during the validate phase I'm going to assume that we will never
                                 # have a case where irb_documents.xls is not loaded ??

        self.load_test_spec("study_sponsors_associate")
        WorkflowService.test_spec("study_sponsors_associate")  # This would raise errors if it didn't validate


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        flask.g.user = UserModel(uid='dhf8r')
        app.config['PB_ENABLED'] = True

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors_associate")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors_associate")
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()
        self.assertTrue(processor.bpmn_workflow.is_completed())
        data = processor.next_task().data
        self.assertIn('sponsors', data)
        self.assertIn('out', data)
        print(data['out'])
        dhf8r_info = LdapSchema().dump(LdapService.user_info('dhf8r'))
        lb3dp_info = LdapSchema().dump(LdapService.user_info('lb3dp'))

        self.assertDictEqual({'uid': 'dhf8r', 'role': 'owner', 'send_email': True, 'access': True, 'ldap_info': dhf8r_info},
                             data['out'][1])
        self.assertDictEqual({'uid': 'lb3dp', 'role': 'SuperDude', 'send_email': False, 'access': True, 'ldap_info': lb3dp_info},
                             data['out'][0])
        self.assertDictEqual({'uid': 'lb3dp', 'role': 'SuperDude', 'send_email': False, 'access': True, 'ldap_info': lb3dp_info},
                             data['out2'])
        self.assertDictEqual({'uid': 'dhf8r', 'role': 'owner', 'send_email': True, 'access': True, 'ldap_info': dhf8r_info},
                             data['out3'][1])
        self.assertDictEqual({'uid': 'lb3dp', 'role': 'SuperGal', 'send_email': False, 'access': True, 'ldap_info': lb3dp_info},
                             data['out3'][0])
        self.assertDictEqual({'uid': 'lb3dp', 'role': 'SuperGal', 'send_email': False, 'access': True, 'ldap_info': lb3dp_info},
                             data['out4'])
        self.assertEqual(3, len(data['sponsors']))


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script_fail(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        flask.g.user = UserModel(uid='dhf8r')
        app.config['PB_ENABLED'] = True

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors_associate_fail")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors_associate_fail")
        processor = WorkflowProcessor(workflow_model)
        with self.assertRaises(ApiError):
            processor.do_engine_steps()


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script_primary_user(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        flask.g.user = UserModel(uid='dhf8r')
        app.config['PB_ENABLED'] = True

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors_associate_switch_user")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors_associate_switch_user")
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()
        tasks = processor.next_user_tasks()
        self.assertEqual(len(tasks),1)
        processor.complete_task(tasks[0])
        processor.do_engine_steps()
        self.assertTrue(processor.bpmn_workflow.is_completed())


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script_valid_users(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        flask.g.user = UserModel(uid='dhf8r')
        app.config['PB_ENABLED'] = True

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors_associate_switch_user")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors_associate_switch_user")
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()
        tasks = processor.next_user_tasks()
        self.assertEqual(len(tasks),1)
        users = WorkflowService.get_users_assigned_to_task(processor,tasks[0])
        self.assertFalse('cah3us' in users)
        self.assertFalse('lje5u' in users)
        self.assertTrue('lb3dp' in users)
        self.assertTrue('dhf8r' in users)
        # the above should emulate what is going on when we determine if a user can
        # make changes to a study or not.
        # in theory all endpoints that need to be limited are calling the
        # WorkflowService.get_users_assigned_to_task function to determine
        # who is allowed access


    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script_ensure_access(self, mock_get, mock_details):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)
        flask.g.user = UserModel(uid='dhf8r')
        app.config['PB_ENABLED'] = True

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors_associate_switch_user")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors_associate_switch_user")
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()
        # change user and make sure we can access the study
        flask.g.user = UserModel(uid='lb3dp')
        flask.g.token = 'my spiffy token'
        app.config['PB_ENABLED'] = False
        output = user_studies()
        self.assertEqual(output[0]['id'], 0)
        self.assertEqual(output[0]['user_uid'], 'dhf8r')
        flask.g.user = UserModel(uid='lje5u')
        flask.g.token = 'my spiffy token'
        app.config['PB_ENABLED'] = False
        output = user_studies()
        self.assertEqual(len(output),0)


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script_ensure_delete(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        flask.g.user = UserModel(uid='dhf8r')
        app.config['PB_ENABLED'] = True

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors_associates_delete")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors_associates_delete")
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()
        # change user and make sure we can access the study
        flask.g.user = UserModel(uid='lb3dp')
        flask.g.token = 'my spiffy token'
        app.config['PB_ENABLED'] = False
        output = user_studies()
        self.assertEqual(len(output),0)
        flask.g.token = 'my spiffy token'
        app.config['PB_ENABLED'] = False
        output = user_studies()
        self.assertEqual(len(output),0)

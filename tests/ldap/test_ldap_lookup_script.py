from tests.base_test import BaseTest

from crc.services.workflow_processor import WorkflowProcessor
from crc.scripts.ldap import Ldap
from crc.api.common import ApiError
from crc import db, mail


class TestLdapLookupScript(BaseTest):

    def test_get_existing_user_details(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()

        script = Ldap()
        user_details = script.do_task(task, workflow.study_id, workflow.id, "dhf8r")

        self.assertEqual(user_details['display_name'], 'Dan Funk')
        self.assertEqual(user_details['given_name'], 'Dan')
        self.assertEqual(user_details['email_address'], 'dhf8r@virginia.edu')
        self.assertEqual(user_details['telephone_number'], '+1 (434) 924-1723')
        self.assertEqual(user_details['title'], 'E42:He\'s a hoopy frood')
        self.assertEqual(user_details['department'], 'E0:EN-Eng Study of Parallel Universes')
        self.assertEqual(user_details['affiliation'], 'faculty')
        self.assertEqual(user_details['sponsor_type'], 'Staff')
        self.assertEqual(user_details['uid'], 'dhf8r')
        self.assertEqual(user_details['proper_name'], 'Dan Funk - (dhf8r)')

    def test_get_invalid_user_details(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()

        task.data = {
          'PIComputingID': 'rec3z'
        }

        script = Ldap()
        with(self.assertRaises(ApiError)):
            user_details = script.do_task(task, workflow.study_id, workflow.id, "PIComputingID")


    def test_bpmn_task_receives_user_details(self):
        workflow = self.create_workflow('ldap_replace')

        task_data = {
          'Supervisor': 'dhf8r',
          'Investigator': 'lb3dp'
        }
        task = self.get_workflow_api(workflow).next_task

        self.complete_form(workflow, task, task_data)

        task = self.get_workflow_api(workflow).next_task

        self.assertEqual(task.data['Supervisor']['display_name'], 'Dan Funk')
        self.assertEqual(task.data['Supervisor']['given_name'], 'Dan')
        self.assertEqual(task.data['Supervisor']['email_address'], 'dhf8r@virginia.edu')
        self.assertEqual(task.data['Supervisor']['telephone_number'], '+1 (434) 924-1723')
        self.assertEqual(task.data['Supervisor']['title'], 'E42:He\'s a hoopy frood')
        self.assertEqual(task.data['Supervisor']['department'], 'E0:EN-Eng Study of Parallel Universes')
        self.assertEqual(task.data['Supervisor']['affiliation'], 'faculty')
        self.assertEqual(task.data['Supervisor']['sponsor_type'], 'Staff')
        self.assertEqual(task.data['Supervisor']['uid'], 'dhf8r')
        self.assertEqual(task.data['Supervisor']['proper_name'], 'Dan Funk - (dhf8r)')
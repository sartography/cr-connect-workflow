from tests.base_test import BaseTest

from crc.services.workflow_processor import WorkflowProcessor
from crc.scripts.ldap_lookup import LdapLookup
from crc import db, mail


class TestLdapLookupScript(BaseTest):

    def test_get_existing_user_details(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()

        task.data = {
          'PIComputingID': 'dhf8r'
        }

        script = LdapLookup()
        user_details = script.do_task(task, workflow.study_id, workflow.id, "PIComputingID")

        self.assertEqual(user_details['PIComputingID']['label'], 'Dan Funk - (dhf8r)')
        self.assertEqual(user_details['PIComputingID']['value'], 'dhf8r')
        self.assertEqual(user_details['PIComputingID']['data']['display_name'], 'Dan Funk')
        self.assertEqual(user_details['PIComputingID']['data']['given_name'], 'Dan')
        self.assertEqual(user_details['PIComputingID']['data']['email_address'], 'dhf8r@virginia.edu')
        self.assertEqual(user_details['PIComputingID']['data']['telephone_number'], '+1 (434) 924-1723')
        self.assertEqual(user_details['PIComputingID']['data']['title'], 'E42:He\'s a hoopy frood')
        self.assertEqual(user_details['PIComputingID']['data']['department'], 'E0:EN-Eng Study of Parallel Universes')
        self.assertEqual(user_details['PIComputingID']['data']['affiliation'], 'faculty')
        self.assertEqual(user_details['PIComputingID']['data']['sponsor_type'], 'Staff')
        self.assertEqual(user_details['PIComputingID']['data']['uid'], 'dhf8r')

    def test_get_invalid_user_details(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()

        task.data = {
          'PIComputingID': 'rec3z'
        }

        script = LdapLookup()
        user_details = script.do_task(task, workflow.study_id, workflow.id, "PIComputingID")
        self.assertEqual(user_details['PIComputingID']['label'], 'invalid uid')
        self.assertEqual(user_details['PIComputingID']['value'], 'rec3z')
        self.assertEqual(user_details['PIComputingID']['data'], {})

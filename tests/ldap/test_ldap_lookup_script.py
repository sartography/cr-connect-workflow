from tests.base_test import BaseTest

from crc.services.workflow_processor import WorkflowProcessor
from crc.scripts.ldap_lookup import LdapReplace
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

        script = LdapReplace()
        user_details = script.do_task(task, workflow.study_id, workflow.id, "PIComputingID")

        self.assertEqual(task.data['PIComputingID']['display_name'], 'Dan Funk')
        self.assertEqual(task.data['PIComputingID']['given_name'], 'Dan')
        self.assertEqual(task.data['PIComputingID']['email_address'], 'dhf8r@virginia.edu')
        self.assertEqual(task.data['PIComputingID']['telephone_number'], '+1 (434) 924-1723')
        self.assertEqual(task.data['PIComputingID']['title'], 'E42:He\'s a hoopy frood')
        self.assertEqual(task.data['PIComputingID']['department'], 'E0:EN-Eng Study of Parallel Universes')
        self.assertEqual(task.data['PIComputingID']['affiliation'], 'faculty')
        self.assertEqual(task.data['PIComputingID']['sponsor_type'], 'Staff')
        self.assertEqual(task.data['PIComputingID']['uid'], 'dhf8r')
        self.assertEqual(task.data['PIComputingID']['proper_name'], 'Dan Funk - (dhf8r)')

    def test_get_existing_users_details(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()

        task.data = {
          'supervisor': 'dhf8r',
          'investigator': 'lb3dp'
        }

        script = LdapReplace()
        user_details = script.do_task(task, workflow.study_id, workflow.id, "supervisor", "investigator")

        self.assertEqual(task.data['supervisor']['display_name'], 'Dan Funk')
        self.assertEqual(task.data['supervisor']['given_name'], 'Dan')
        self.assertEqual(task.data['supervisor']['email_address'], 'dhf8r@virginia.edu')
        self.assertEqual(task.data['supervisor']['telephone_number'], '+1 (434) 924-1723')
        self.assertEqual(task.data['supervisor']['title'], 'E42:He\'s a hoopy frood')
        self.assertEqual(task.data['supervisor']['department'], 'E0:EN-Eng Study of Parallel Universes')
        self.assertEqual(task.data['supervisor']['affiliation'], 'faculty')
        self.assertEqual(task.data['supervisor']['sponsor_type'], 'Staff')
        self.assertEqual(task.data['supervisor']['uid'], 'dhf8r')
        self.assertEqual(task.data['supervisor']['proper_name'], 'Dan Funk - (dhf8r)')

        self.assertEqual(task.data['investigator']['display_name'], 'Laura Barnes')
        self.assertEqual(task.data['investigator']['given_name'], 'Laura')
        self.assertEqual(task.data['investigator']['email_address'], 'lb3dp@virginia.edu')
        self.assertEqual(task.data['investigator']['telephone_number'], '+1 (434) 924-1723')
        self.assertEqual(task.data['investigator']['title'], 'E0:Associate Professor of Systems and Information Engineering')
        self.assertEqual(task.data['investigator']['department'], 'E0:EN-Eng Sys and Environment')
        self.assertEqual(task.data['investigator']['affiliation'], 'faculty')
        self.assertEqual(task.data['investigator']['sponsor_type'], 'Staff')
        self.assertEqual(task.data['investigator']['uid'], 'lb3dp')
        self.assertEqual(task.data['investigator']['proper_name'], 'Laura Barnes - (lb3dp)')

    def test_get_invalid_user_details(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()

        task.data = {
          'PIComputingID': 'rec3z'
        }

        script = LdapReplace()
        user_details = script.do_task(task, workflow.study_id, workflow.id, "PIComputingID")

        self.assertEqual(task.data['PIComputingID'], {})

    def test_bpmn_task_receives_user_details(self):
        workflow = self.create_workflow('ldap_replace')

        task_data = {
          'Supervisor': 'dhf8r',
          'Investigator': 'lb3dp'
        }
        task = self.get_workflow_api(workflow).next_task

        self.complete_form(workflow, task, task_data)

        task = self.get_workflow_api(workflow).next_task

        self.assertEqual(task.data['Supervisor']['proper_name'], 'Dan Funk - (dhf8r)')

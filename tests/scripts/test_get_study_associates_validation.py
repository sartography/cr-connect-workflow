from tests.base_test import BaseTest

from crc import session
from crc.models.ldap import LdapModel
from crc.models.study import StudyAssociated
from crc.services.workflow_service import WorkflowService


class TestStudyAssociatesValidation(BaseTest):

    @staticmethod
    def add_study_associated(workflow):
        ldap_model = session.query(LdapModel).first()
        study_associated = StudyAssociated(study_id=workflow.study_id,
                                           uid=ldap_model.uid,
                                           role='Department Chair',
                                           send_email=True,
                                           access=True,
                                           ldap_info=ldap_model)
        session.add(study_associated)
        study_associated = StudyAssociated(study_id=workflow.study_id,
                                           uid=ldap_model.uid,
                                           role='Primary Investigator',
                                           send_email=True,
                                           access=True,
                                           ldap_info=ldap_model)
        session.add(study_associated)
        study_associated = StudyAssociated(study_id=workflow.study_id,
                                           uid=ldap_model.uid,
                                           role='Study Coordinator I',
                                           send_email=True,
                                           access=True,
                                           ldap_info=ldap_model)
        session.add(study_associated)
        session.commit()

    def test_study_associates_validation_with_study_id(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        workflow = self.create_workflow('study_associates_validation')
        self.add_study_associated(workflow)
        rv = self.app.get('/v1.0/workflow-specification/%s/validate?study_id=%i' % (workflow.workflow_spec_id, workflow.study_id),
                          headers=self.logged_in_headers())
        self.assertEqual(0, len(rv.json))

    def test_study_associates_validation_without_study_id(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        workflow = self.create_workflow('study_associates_validation')
        self.add_study_associated(workflow)
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % workflow.workflow_spec_id,
                          headers=self.logged_in_headers())
        self.assertEqual(0, len(rv.json))

    def test_study_associates_test_spec_with_study(self):
        # call test_spec directly so we can see what the script actually returns
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        workflow = self.create_workflow('study_associates_validation')
        self.add_study_associated(workflow)
        result = WorkflowService.test_spec('study_associates_validation', validate_study_id=workflow.study_id)

        # assert we get information we added with add_study_associated
        self.assertIsInstance(result['assoc_info'], dict)
        self.assertEqual('New', result['assoc_status'])
        self.assertEqual(4, len(result['assoc_list']))
        self.assertEqual(result['assoc_role'], result['assoc_info']['role'])
        self.assertIn(result['assoc_role'], ['Department Chair', 'Primary Investigator', 'Study Coordinator I'])

    def test_study_associates_test_spec_no_study(self):

        # call test_spec directly so we can see what the script actually returns
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        workflow = self.create_workflow('study_associates_validation')
        self.add_study_associated(workflow)
        result = WorkflowService.test_spec('study_associates_validation')

        # assert we get mock information
        self.assertIn(result['assoc_role_enum'], ['pi', 'dc', 'sc_i'])
        self.assertIsNone(result['assoc_info'])
        self.assertEqual('Not Found', result['assoc_status'])
        self.assertEqual('test', result['assoc_list'][0]['uid'])
        self.assertEqual('owner', result['assoc_list'][0]['role'])

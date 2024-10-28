import json
from datetime import datetime
from unittest.mock import patch
from unittest import skip

from tests.base_test import BaseTest

from crc import db, app
from crc.models.study import StudyModel, StudyStatus, StudyAssociatedSchema, CategoryMetadata, StudySchema, \
    CategorySchema, Category
from crc.models.user import UserModel
from crc.models.workflow import WorkflowModel, WorkflowStatus, WorkflowSpecCategory, WorkflowSpecCategorySchema
from crc.services.ldap_service import LdapService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.user_file_service import UserFileService
from crc.services.user_service import UserService
from crc.services.workflow_spec_service import WorkflowSpecService


class TestStudyService(BaseTest):
    """Largely tested via the test_study_api, and time is tight, but adding new tests here."""

    def create_user_with_study_and_workflow(self):
        self.load_test_spec("top_level_workflow", master_spec=True)
        cat = WorkflowSpecCategory(id="approvals", display_name="Approvals", display_order=0, admin=False)
        self.workflow_spec_service.add_category(cat)
        self.load_test_spec("random_fact", category_id=cat.id)
        user = self.create_user()
        study = StudyModel(title="My title", status=StudyStatus.in_progress, user_uid=user.uid, review_type=2)
        db.session.add(study)
        db.session.commit()
        self.assertIsNotNone(study.id)
        workflow = WorkflowModel(workflow_spec_id="random_fact", study_id=study.id,
                                 status=WorkflowStatus.not_started, last_updated=datetime.utcnow())
        db.session.add(workflow)
        db.session.commit()
        return user

    @skip("We don't actually use this feature.")
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    def test_study_progress(self, mock_docs, mock_details):
        """Assure that as a users progress is available when getting a list of studies for that user."""
        app.config['PB_ENABLED'] = True
        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)

        user = self.create_user_with_study_and_workflow()

        # The load example data script should set us up a user and at least one study, one category, and one workflow.
        spec_service = WorkflowSpecService()
        categories = spec_service.get_categories()
        studies = StudyService().get_studies_for_user(user, categories)

        self.assertTrue(len(studies) == 1)
        self.assertEqual(0, studies[0].progress)

        # Initialize the Workflow with the workflow processor.
        workflow_model = db.session.query(WorkflowModel).filter(WorkflowModel.study_id == studies[0].id).first()
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()

        # Complete a task
        task = processor.next_task()
        task.data = {"type":"norris"}
        processor.complete_task(task)
        processor.do_engine_steps()
        processor.save()

        # Assure the progress is now updated
        studies = StudyService().get_studies_for_user(user, categories)
        self.assertGreater(studies[0].progress, 0)


    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    def test_get_required_docs(self, mock_docs, mock_details):
        self.create_reference_document()
        app.config['PB_ENABLED'] = True
        # mock out the protocol builder
        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)

        user = self.create_user_with_study_and_workflow()
        spec_service = WorkflowSpecService()
        categories = spec_service.get_categories()
        studies = StudyService().get_studies_for_user(user, categories)
        study = studies[0]


        study_service = StudyService()
        documents = study_service.get_documents_status(study_id=study.id, force=True)  # Mocked out, any random study id works.
        self.assertIsNotNone(documents)
        self.assertTrue("UVACompl_PRCAppr" in documents.keys())
        self.assertEqual("UVACompl_PRCAppr", documents["UVACompl_PRCAppr"]['code'])
        self.assertEqual("UVA Compliance / PRC Approval", documents["UVACompl_PRCAppr"]['display_name'])
        self.assertEqual("Cancer Center's PRC Approval Form", documents["UVACompl_PRCAppr"]['description'])
        self.assertEqual("UVA Compliance", documents["UVACompl_PRCAppr"]['category1'])
        self.assertEqual("PRC Approval", documents["UVACompl_PRCAppr"]['category2'])
        self.assertEqual("", documents["UVACompl_PRCAppr"]['category3'])
        self.assertEqual("Study Team", documents["UVACompl_PRCAppr"]['who_uploads?'])
        self.assertEqual(0, documents["UVACompl_PRCAppr"]['count'])
        self.assertEqual(True, documents["UVACompl_PRCAppr"]['required'])
        self.assertEqual(6, documents["UVACompl_PRCAppr"]['id'])

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    def test_get_documents_has_file_details(self, mock_docs):
        self.create_reference_document()
        # mock out the protocol builder
        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)

        user = self.create_user_with_study_and_workflow()

        # Add a document to the study with the correct code.
        workflow = self.create_workflow('docx')
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name='t1',
                                          name="anything.png", content_type="text",
                                          binary_data=b'1234', irb_doc_code=irb_code)

        docs = StudyService().get_documents_status(workflow.study_id)
        self.assertIsNotNone(docs)
        self.assertEqual("not_started", docs["UVACompl_PRCAppr"]['status'])
        self.assertEqual(1, docs["UVACompl_PRCAppr"]['count'])
        self.assertIsNotNone(docs["UVACompl_PRCAppr"]['files'][0])
        self.assertIsNotNone(docs["UVACompl_PRCAppr"]['files'][0]['id'])
        self.assertEqual(workflow.id, docs["UVACompl_PRCAppr"]['files'][0]['workflow_id'])

    def test_get_all_studies(self):
        user = self.create_user_with_study_and_workflow()
        study = db.session.query(StudyModel).filter_by(user_uid=user.uid).first()
        self.assertIsNotNone(study)

        # Add a document to the study with the correct code.
        workflow1 = self.create_workflow('docx', study=study)
        workflow2 = self.create_workflow('empty_workflow', study=study)

        # Add files to both workflows.
        UserFileService.add_workflow_file(workflow_id=workflow1.id,
                                          task_spec_name="t1",
                                          name="anything.png", content_type="text",
                                          binary_data=b'1234', irb_doc_code="UVACompl_PRCAppr" )
        UserFileService.add_workflow_file(workflow_id=workflow1.id,
                                          task_spec_name="t1",
                                          name="anything.png", content_type="text",
                                          binary_data=b'1234', irb_doc_code="AD_Consent_Model")
        UserFileService.add_workflow_file(workflow_id=workflow2.id,
                                          task_spec_name="t1",
                                          name="anything.png", content_type="text",
                                          binary_data=b'1234', irb_doc_code="UVACompl_PRCAppr" )

        studies = StudyService().get_all_studies_with_files()
        self.assertEqual(1, len(studies))
        self.assertEqual(3, len(studies[0].files))




    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')  # mock_docs
    def test_get_personnel_roles(self, mock_docs):
        self.create_reference_document()

        # mock out the protocol builder
        docs_response = self.protocol_builder_response('investigators.json')
        mock_docs.return_value = json.loads(docs_response)

        workflow = self.create_workflow('docx') # The workflow really doesnt matter in this case.
        investigators = StudyService().get_investigators(workflow.study_id, all=True)

        self.assertEqual(10, len(investigators))

        # dhf8r is in the ldap mock data.
        self.assertEqual("dhf8r", investigators['PI']['user_id'])
        self.assertEqual("Dan Funk", investigators['PI']['display_name']) # Data from ldap
        self.assertEqual("Primary Investigator", investigators['PI']['label']) # Data from xls file.
        self.assertEqual("Always", investigators['PI']['display']) # Data from xls file.

        # asd3v is not in ldap, so an error should be returned.
        self.assertEqual("asd3v", investigators['DC']['user_id'])
        self.assertEqual("ApiError: Unable to locate a user with id asd3v in LDAP. ", investigators['DC']['error']) # Data from ldap

        # No value is provided for Department Chair
        self.assertIsNone(investigators['DEPT_CH']['user_id'])

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')  # mock_docs
    def test_get_study_personnel(self, mock_docs):
        self.create_reference_document()

        # mock out the protocol builder
        docs_response = self.protocol_builder_response('investigators.json')
        mock_docs.return_value = json.loads(docs_response)

        workflow = self.create_workflow('docx') # The workflow really doesnt matter in this case.
        investigators = StudyService().get_investigators(workflow.study_id, all=False)

        self.assertEqual(5, len(investigators))

        # dhf8r is in the ldap mock data.
        self.assertEqual("dhf8r", investigators['PI']['user_id'])
        self.assertEqual("Dan Funk", investigators['PI']['display_name']) # Data from ldap
        self.assertEqual("Primary Investigator", investigators['PI']['label']) # Data from xls file.
        self.assertEqual("Always", investigators['PI']['display']) # Data from xls file.

        # Both Alex and Aaron are SI, and both should be returned.
        self.assertEqual("ajl2j", investigators['SI']['user_id'])
        self.assertEqual("cah3us", investigators['SI_2']['user_id'])

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    def test_get_user_studies(self, mock_details):
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)

        user = self.create_user_with_study_and_workflow()
        spec_service = WorkflowSpecService()
        categories = spec_service.get_categories()
        studies = StudyService().get_studies_for_user(user, categories)
        # study_details has a valid REVIEW_TYPE, so we should get 1 study back
        self.assertEqual(1, len(studies))

    def test_get_user_studies_bad_review_type(self):
        spec_service = WorkflowSpecService()
        categories = spec_service.get_categories()
        user = self.create_user_with_study_and_workflow()
        study = db.session.query(StudyModel).first()
        study.review_type = 1984 # A particularly bad review type.
        db.session.commit()
        studies = StudyService().get_studies_for_user(user, categories)
        # study_details has an invalid REVIEW_TYPE, so we should get 0 studies back
        self.assertEqual(0, len(studies))

    def test_study_associates(self):
        self.create_user_with_study_and_workflow()
        study = db.session.query(StudyModel).first()
        self.create_user(uid='lb3dp', email='lb3dp@example.com', display_name='lb3dp')
        StudyService.update_study_associate(study_id=study.id, uid='lb3dp', role='Primary Investigator', send_email=True, access=True)
        associates = StudyService.get_study_associates(study.id)
        # get_study_associates always returns the owner of the study.
        # so we should get 2 associates back.
        self.assertEquals(2, len(associates))
        assoc_json = StudyAssociatedSchema(many=True).dump(associates)
        self.assertEquals("Dan", assoc_json[1]['ldap_info']['given_name'])
        self.assertEqual('Primary Investigator', assoc_json[0]['role'])
        self.assertEqual('Laura Barnes', assoc_json[0]['ldap_info']['display_name'])

    def test_set_category_metadata(self):
        user = self.create_user_with_study_and_workflow()
        study = db.session.query(StudyModel).filter_by(user_uid=user.uid).first()

        ####
        wfscat = WorkflowSpecCategory(id='test_cat', display_name='test cat', display_order=0, admin=False)
        wfs = self.create_workflow('empty_workflow')

        wfscat.workflows = wfs
        x = WorkflowSpecCategorySchema().dump(wfscat)
        ####

        s = StudyService.get_study(study.id, [wfscat], None, {'test_cat':{'status':'hidden', 'message': 'msg'}}, process_categories=True)
        d = StudySchema().dump(s)
        self.assertEqual({'id': 'test_cat', 'message': 'msg', 'state': 'hidden'}, d['categories'][0]['meta'])





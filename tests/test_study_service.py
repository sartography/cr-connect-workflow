import json
from datetime import datetime
from unittest.mock import patch

from crc import db
from crc.models.protocol_builder import ProtocolBuilderStatus
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowModel, WorkflowStatus, \
    WorkflowSpecCategoryModel
from crc.services.file_service import FileService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from example_data import ExampleDataLoader
from tests.base_test import BaseTest


class TestStudyService(BaseTest):
    """Largely tested via the test_study_api, and time is tight, but adding new tests here."""

    def create_user_with_study_and_workflow(self):

        # clear it all out.
        from example_data import ExampleDataLoader
        ExampleDataLoader.clean_db()

        # Assure some basic models are in place, This is a damn mess.  Our database models need an overhaul to make
        # this easier - better relationship modeling is now critical.
        self.load_test_spec("top_level_workflow", master_spec=True)
        user = db.session.query(UserModel).filter(UserModel.uid == "dhf8r").first()
        if not user:
            user = UserModel(uid="dhf8r", email_address="whatever@stuff.com", display_name="Stayathome Smellalots")
            db.session.add(user)
            db.session.commit()
        else:
            for study in db.session.query(StudyModel).all():
                StudyService().delete_study(study.id)

        study = StudyModel(title="My title", protocol_builder_status=ProtocolBuilderStatus.ACTIVE, user_uid=user.uid)
        db.session.add(study)
        cat = WorkflowSpecCategoryModel(name="approvals", display_name="Approvals", display_order=0)
        db.session.add(cat)
        db.session.commit()

        self.assertIsNotNone(cat.id)
        self.load_test_spec("random_fact", category_id=cat.id)

        self.assertIsNotNone(study.id)
        workflow = WorkflowModel(workflow_spec_id="random_fact", study_id=study.id,
                                 status=WorkflowStatus.not_started, last_updated=datetime.now())
        db.session.add(workflow)
        db.session.commit()
        # Assure there is a master specification, one standard spec, and lookup tables.
        ExampleDataLoader().load_reference_documents()
        return user

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    def test_total_tasks_updated(self, mock_docs):
        """Assure that as a users progress is available when getting a list of studies for that user."""

        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)

        user = self.create_user_with_study_and_workflow()

        # The load example data script should set us up a user and at least one study, one category, and one workflow.
        studies = StudyService.get_studies_for_user(user)
        self.assertTrue(len(studies) == 1)
        self.assertTrue(len(studies[0].categories) == 1)
        self.assertTrue(len(studies[0].categories[0].workflows) == 1)

        workflow = next(iter(studies[0].categories[0].workflows)) # Workflows is a set.

        # workflow should not be started, and it should have 0 completed tasks, and 0 total tasks.
        self.assertEqual(WorkflowStatus.not_started, workflow.status)
        self.assertEqual(None, workflow.spec_version)
        self.assertEqual(0, workflow.total_tasks)
        self.assertEqual(0, workflow.completed_tasks)

        # Initialize the Workflow with the workflow processor.
        workflow_model = db.session.query(WorkflowModel).filter(WorkflowModel.id == workflow.id).first()
        processor = WorkflowProcessor(workflow_model)

        # Assure the workflow is now started, and knows the total and completed tasks.
        studies = StudyService.get_studies_for_user(user)
        workflow = next(iter(studies[0].categories[0].workflows)) # Workflows is a set.
#        self.assertEqual(WorkflowStatus.user_input_required, workflow.status)
        self.assertTrue(workflow.total_tasks > 0)
        self.assertEqual(0, workflow.completed_tasks)
        self.assertIsNotNone(workflow.spec_version)

        # Complete a task
        task = processor.next_task()
        processor.complete_task(task)
        processor.save()

        # Assure the workflow has moved on to the next task.
        studies = StudyService.get_studies_for_user(user)
        workflow = next(iter(studies[0].categories[0].workflows)) # Workflows is a set.
        self.assertEqual(1, workflow.completed_tasks)

        # Get approvals
        approvals = StudyService.get_approvals(studies[0].id)
        self.assertGreater(len(approvals), 0)
        self.assertIsNotNone(approvals[0]['display_order'])

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    def test_get_required_docs(self, mock_docs):

        # mock out the protocol builder
        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)

        user = self.create_user_with_study_and_workflow()
        studies = StudyService.get_studies_for_user(user)
        study = studies[0]


        study_service = StudyService()
        documents = study_service.get_documents_status(study_id=study.id)  # Mocked out, any random study id works.
        self.assertIsNotNone(documents)
        self.assertTrue("UVACompl_PRCAppr" in documents.keys())
        self.assertEqual("UVACompl_PRCAppr", documents["UVACompl_PRCAppr"]['code'])
        self.assertEqual("UVA Compliance / PRC Approval", documents["UVACompl_PRCAppr"]['display_name'])
        self.assertEqual("Cancer Center's PRC Approval Form", documents["UVACompl_PRCAppr"]['description'])
        self.assertEqual("UVA Compliance", documents["UVACompl_PRCAppr"]['category1'])
        self.assertEqual("PRC Approval", documents["UVACompl_PRCAppr"]['category2'])
        self.assertEqual("", documents["UVACompl_PRCAppr"]['category3'])
        self.assertEqual("CRC", documents["UVACompl_PRCAppr"]['Who Uploads?'])
        self.assertEqual(0, documents["UVACompl_PRCAppr"]['count'])
        self.assertEqual(True, documents["UVACompl_PRCAppr"]['required'])
        self.assertEqual('6', documents["UVACompl_PRCAppr"]['id'])

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    def test_get_documents_has_file_details(self, mock_docs):

        # mock out the protocol builder
        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)

        user = self.create_user_with_study_and_workflow()

        # Add a document to the study with the correct code.
        workflow = self.create_workflow('docx')
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_task_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  workflow_spec_id=workflow.workflow_spec_id,
                                  task_id="fakingthisout",
                                  name="anything.png", content_type="text",
                                  binary_data=b'1234', irb_doc_code=irb_code)

        docs = StudyService().get_documents_status(workflow.study_id)
        self.assertIsNotNone(docs)
        self.assertEqual("not_started", docs["UVACompl_PRCAppr"]['status'])
        self.assertEqual(1, docs["UVACompl_PRCAppr"]['count'])
        self.assertIsNotNone(docs["UVACompl_PRCAppr"]['files'][0])
        self.assertIsNotNone(docs["UVACompl_PRCAppr"]['files'][0]['file_id'])
        self.assertEquals(workflow.id, docs["UVACompl_PRCAppr"]['files'][0]['workflow_id'])
        self.assertEquals(workflow.workflow_spec_id, docs["UVACompl_PRCAppr"]['files'][0]['workflow_spec_id'])

    # 'file_id': 123,
    # 'task_id': 'abcdef14236890',
    # 'workflow_id': 456,
    # 'workflow_spec_id': 'irb_api_details',
    # 'status': 'complete',

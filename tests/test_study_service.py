import json
from unittest.mock import patch

from crc import db
from crc.models.protocol_builder import ProtocolBuilderStatus
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowModel, WorkflowStatus, \
    WorkflowSpecCategoryModel
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from example_data import ExampleDataLoader
from tests.base_test import BaseTest


class TestStudyService(BaseTest):
    """Largely tested via the test_study_api, and time is tight, but adding new tests here."""

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    def test_total_tasks_updated(self, mock_docs):
        """Assure that as a users progress is available when getting a list of studies for that user."""

        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)

        # Assure some basic models are in place, This is a damn mess.  Our database models need an overhaul to make
        # this easier - better relationship modeling is now critical.
        self.load_test_spec("top_level_workflow", master_spec=True)
        user = UserModel(uid="dhf8r", email_address="whatever@stuff.com", display_name="Stayathome Smellalots")
        db.session.add(user)
        db.session.commit()
        study = StudyModel(title="My title", protocol_builder_status=ProtocolBuilderStatus.ACTIVE, user_uid=user.uid)
        cat = WorkflowSpecCategoryModel(name="approvals", display_name="Approvals", display_order=0)
        db.session.add_all([study, cat])
        db.session.commit()

        self.assertIsNotNone(cat.id)
        self.load_test_spec("random_fact", category_id=cat.id)

        self.assertIsNotNone(study.id)
        workflow = WorkflowModel(workflow_spec_id="random_fact", study_id=study.id, status=WorkflowStatus.not_started)
        db.session.add(workflow)
        db.session.commit()
        # Assure there is a master specification, one standard spec, and lookup tables.
        ExampleDataLoader().load_reference_documents()

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

        # Assure the workflow has moved on to the next task.
        studies = StudyService.get_studies_for_user(user)
        workflow = next(iter(studies[0].categories[0].workflows)) # Workflows is a set.
        self.assertEqual(1, workflow.completed_tasks)

        # Get approvals
        approvals = StudyService.get_approvals(studies[0].id)
        self.assertGreater(len(approvals), 0)

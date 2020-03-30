import json
from datetime import datetime, timezone
from unittest.mock import patch

from crc import session, db
from crc.models.api_models import WorkflowApiSchema
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudyDetailsSchema, \
    ProtocolBuilderStudySchema
from crc.models.study import StudyModel, StudySchema
from crc.models.user import UserModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus, \
    WorkflowSpecCategoryModel
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from tests.base_test import BaseTest


class TestStudyService(BaseTest):
    """Largely tested via the test_study_api, and time is tight, but adding new tests here."""

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')  # mock_studies
    def test_total_tasks_updated(self, mock_studies, mock_details):
        """Assure that as a user makes progress"""
        self.load_example_data()

        # Mock Protocol Builder responses
        studies_response = self.protocol_builder_response('user_studies.json')
        mock_studies.return_value = ProtocolBuilderStudySchema(many=True).loads(studies_response)
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = ProtocolBuilderStudyDetailsSchema().loads(details_response)

        # The load example data script should set us up a user and at least one study, one category, and one workflow.
        user = db.session.query(UserModel).first()
        studies = StudyService.get_studies_for_user(user)
        self.assertTrue(len(studies) > 1)
        self.assertTrue(len(studies[0].categories) > 1)
        self.assertTrue(len(studies[0].categories[0].workflows) > 1)

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

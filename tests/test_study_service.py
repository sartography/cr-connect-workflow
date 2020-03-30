import json
from datetime import datetime, timezone
from unittest.mock import patch

from crc import session
from crc.models.api_models import WorkflowApiSchema
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudyDetailsSchema, \
    ProtocolBuilderStudySchema
from crc.models.study import StudyModel, StudySchema
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus, \
    WorkflowSpecCategoryModel
from tests.base_test import BaseTest


class TestStudyService(BaseTest):


    def test_total_tasks_updated(self):
        """Assure that as a user makes progress"""
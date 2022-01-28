import json
import unittest
from tests.base_test import BaseTest

from crc.models.workflow import WorkflowSpecCategoryModel, WorkflowSpecModel
from crc.services.workflow_sync import WorkflowSyncService
from crc import db


class TestWorkflowSync(BaseTest):

    def test_clear_data(self):
        self.load_example_data()

        self.assertFalse(db.session.query(WorkflowSpecCategoryModel).count() == 0)
        self.assertFalse(db.session.query(WorkflowSpecModel).count() == 0)

        WorkflowSyncService.clear_database()
        self.assertTrue(db.session.query(WorkflowSpecCategoryModel).count() == 0)
        self.assertTrue(db.session.query(WorkflowSpecModel).count() == 0)

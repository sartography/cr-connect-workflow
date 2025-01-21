import json
import os
import shutil

from tests.base_test import BaseTest

from crc.models.workflow import WorkflowSpecInfo, WorkflowSpecCategory
from crc.services.file_system_service import FileSystemService
from crc.services.spec_file_service import SpecFileService
from crc.services.workflow_spec_service import WorkflowSpecService
from crc import db, app


class TestWorkflowSync(BaseTest):

    spec_path = FileSystemService.root_path()
    import_spec_path = os.path.join(app.root_path, '..', 'tests', 'data', 'IMPORT_TEST')
    service = WorkflowSpecService()

    def build_file_system_from_models(self):
        """Some tests check to see what happens when we write data to an empty file system."""

        # Construct Two Categories, with one workflow in first category, two in the second.
        # assure that the data in categories.json is correct
        # and that there is the correct data structure.
        c1 = self.assure_category_name_exists("Category Number One")
        c2 = self.assure_category_name_exists("Category Number Two")
        self.load_test_spec('random_fact', category_id=c1.id)
        self.load_test_spec('hello_world', category_id=c2.id)
        self.load_test_spec('decision_table', category_id=c2.id)
        self.load_test_spec('empty_workflow', category_id=c1.id, master_spec=True)
        self.load_test_spec('email', category_id=c1.id, library=True)
        # fixme: add a standalone

    def test_from_file_system_blank_slate(self):
        self.assertEqual(0, len(self.service.get_categories()))
        self.assertEqual(0, len(self.service.get_specs()))

        self.copy_files_to_file_system(self.import_spec_path, self.spec_path)
        self.assertEqual(2, len(self.service.get_categories()))
        self.assertEqual(3, len(self.service.get_specs()))
        self.assertEqual(1, len(self.service.get_category('category_number_one').specs))
        self.assertEqual(2, len(self.service.get_category('category_number_two').specs))
        self.assertIsNotNone(self.service.master_spec)
        self.assertEqual(1, len(self.service.get_libraries()))
        self.assertEqual(1, len(self.service.master_spec.libraries))

    def test_delete_category_and_workflows(self):
        self.copy_files_to_file_system(self.import_spec_path, self.spec_path)
        cat_path = SpecFileService().category_path('category_number_one')
        shutil.rmtree(cat_path) # Remove the path, as if from a git pull and the path was removed.
        self.assertEqual(1, len(self.service.get_categories()))
        self.assertEqual(2, len(self.service.get_specs()))

    def test_create_file_system(self):
        self.build_file_system_from_models()

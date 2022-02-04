import json
import os
import shutil

from tests.base_test import BaseTest

from crc.services.workflow_sync import WorkflowSyncService
from crc.models.workflow import WorkflowSpecInfo, WorkflowSpecCategory
from crc.services.file_system_service import FileSystemService
from crc.services.spec_file_service import SpecFileService
from crc import db, app


class TestWorkflowSync(BaseTest):

    spec_path = FileSystemService.root_path()
    import_spec_path = os.path.join(app.root_path, '..', 'tests', 'data', 'IMPORT_TEST')

    def set_up_file_system(self):
        """Some tests rely on a well populated file system and an empty database to start"""
        shutil.copytree(self.import_spec_path, self.spec_path)

    def set_up_database(self):
        """Some tests rely on a well populated database and an empty file system to start"""

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

    def test_from_file_system_blank_slate(self):
        self.assertEquals(0, len(db.session.query(WorkflowSpecModel).all()))
        self.assertEquals(0, len(db.session.query(WorkflowSpecCategoryModel).all()))
        self.set_up_file_system()
        WorkflowSyncService().from_file_system()
        self.assertEquals(2, len(db.session.query(WorkflowSpecCategoryModel).all()))
        self.assertEquals(5, len(db.session.query(WorkflowSpecModel).all()))
        self.assertEquals(1, len(db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.category_id == 1).all()))
        self.assertEquals(2, len(db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.category_id == 2).all()))
        self.assertEquals(1, len(db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.is_master_spec).all()))
        self.assertEquals(1, len(db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.library).all()))
        # The top level workflow, has a library
        tlw = db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.is_master_spec).first()
        self.assertEquals(1, len(tlw.libraries))

    def test_repeated_imports(self):
        self.set_up_file_system()
        WorkflowSyncService().from_file_system()
        WorkflowSyncService().from_file_system()
        WorkflowSyncService().from_file_system()
        self.assertEquals(2, len(db.session.query(WorkflowSpecCategoryModel).all()))
        self.assertEquals(5, len(db.session.query(WorkflowSpecModel).all()))

    def test_delete_category_and_workflows(self):
        self.set_up_file_system()
        WorkflowSyncService().from_file_system()
        cat_path = SpecFileService().category_path('Category Number One')
        shutil.rmtree(cat_path)
        WorkflowSyncService().from_file_system()
        self.assertEquals(1, len(db.session.query(WorkflowSpecCategoryModel).all()))
        self.assertEquals(4, len(db.session.query(WorkflowSpecModel).all()))
        self.assertEquals(0, len(db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.category_id == 1).all()))

        WorkflowSyncService().to_file_system()
        json_path = os.path.join(FileSystemService.root_path(), "categories.json")
        with open(json_path) as json_file:
            data = json.load(json_file)
            self.assertEquals(1, len(data['categories']), "When the json file is written back to disk, there is only one category now.")

    def test_to_file_system(self):
        """Assure we get the basic paths on the file system that we would expect."""
        self.assertFalse(os.path.exists(self.spec_path))
        self.set_up_database()
        self.assertEqual(4, len(os.listdir(self.spec_path)), "Adding workflows should create dir structure")
        WorkflowSyncService().to_file_system()
        self.assertEqual(5, len(os.listdir(self.spec_path)), "Sync service should create categories.json file")

    def test_to_file_system_correct_categories(self):
        """Assure we have two categories in the json file, and that these directories exist, and contain
           workflow.json files for each workflow."""
        self.set_up_database()
        WorkflowSyncService().to_file_system()
        json_path = os.path.join(self.spec_path, 'categories.json')

        with open(json_path) as json_file:
            data = json.load(json_file)
        self.assertTrue('categories' in data)
        self.assertEqual(2, len(data['categories']))
        counter = 0
        for c in data['categories']:
            cat_path = os.path.join(self.spec_path, c['display_name'])
            self.assertTrue(os.path.exists(cat_path), "The category directories exist.")
            self.assertEqual(data['categories'][counter]['display_order'], counter, "Order is correct")
            counter += 1
            workflow_dirs = os.listdir(cat_path)
            for wd in workflow_dirs:
                wf_json_path = os.path.join(cat_path, wd, 'workflow.json')
                self.assertTrue(os.path.exists(wf_json_path), "A workflow.json file should exist.")
        # Fixme: Assure the master workflow spec, and Libraries are also exported to file system.


    # Todo:
    #  * What if category json files, and directories don't match?
    #  * Test renaming a category
    #  * Test moving a workflow to a different category

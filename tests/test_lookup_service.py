import os

from tests.base_test import BaseTest

from crc.services.file_service import FileService
from crc.api.common import ApiError
from crc import session, app
from crc.models.file import FileDataModel, FileModel, LookupFileModel, LookupDataModel, CONTENT_TYPES
from crc.services.lookup_service import LookupService
from crc.services.workflow_processor import WorkflowProcessor


class TestLookupService(BaseTest):

    def test_lookup_returns_good_error_on_bad_field(self):
        spec = BaseTest.load_test_spec('enum_options_with_search')
        workflow = self.create_workflow('enum_options_with_search')
        file_model = session.query(FileModel).filter(FileModel.name == "customer_list.xls").first()
        file_data_model = session.query(FileDataModel).filter(FileDataModel.file_model == file_model).first()
        with self.assertRaises(ApiError):
            LookupService.lookup(workflow, "not_the_right_field", "sam", limit=10)

    def test_lookup_table_is_not_created_more_than_once(self):
        spec = BaseTest.load_test_spec('enum_options_with_search')
        workflow = self.create_workflow('enum_options_with_search')
        LookupService.lookup(workflow, "sponsor", "sam", limit=10)
        LookupService.lookup(workflow, "sponsor", "something", limit=10)
        LookupService.lookup(workflow, "sponsor", "blah", limit=10)
        lookup_records = session.query(LookupFileModel).all()
        self.assertIsNotNone(lookup_records)
        self.assertEqual(1, len(lookup_records))
        lookup_record = lookup_records[0]
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_record).all()
        self.assertEquals(28, len(lookup_data))

    def test_updates_to_file_cause_lookup_rebuild(self):
        spec = BaseTest.load_test_spec('enum_options_with_search')
        workflow = self.create_workflow('enum_options_with_search')
        file_model = session.query(FileModel).filter(FileModel.name == "sponsors.xls").first()
        LookupService.lookup(workflow, "sponsor", "sam", limit=10)
        lookup_records = session.query(LookupFileModel).all()
        self.assertIsNotNone(lookup_records)
        self.assertEqual(1, len(lookup_records))
        lookup_record = lookup_records[0]
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_record).all()
        self.assertEquals(28, len(lookup_data))

        # Update the workflow specification file.
        file_path = os.path.join(app.root_path, '..', 'tests', 'data',
                                 'enum_options_with_search', 'sponsors_modified.xls')
        file = open(file_path, 'rb')
        FileService.update_file(file_model, file.read(), CONTENT_TYPES['xls'])
        file.close()

        # restart the workflow, so it can pick up the changes.
        WorkflowProcessor(workflow, soft_reset=True)

        LookupService.lookup(workflow, "sponsor", "sam", limit=10)
        lookup_records = session.query(LookupFileModel).all()
        lookup_record = lookup_records[0]
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_record).all()
        self.assertEquals(4, len(lookup_data))



    def test_some_full_text_queries(self):
        spec = BaseTest.load_test_spec('enum_options_from_file')
        workflow = self.create_workflow('enum_options_from_file')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        results = LookupService.lookup(workflow, "AllTheNames", "", limit=10)
        self.assertEquals(10, len(results), "Blank queries return everything, to the limit")

        results = LookupService.lookup(workflow, "AllTheNames", "medicines", limit=10)
        self.assertEquals(1, len(results), "words in the middle of label are detected.")
        self.assertEquals("The Medicines Company", results[0].label)

        results = LookupService.lookup(workflow, "AllTheNames", "UVA", limit=10)
        self.assertEquals(1, len(results), "Beginning of label is found.")
        self.assertEquals("UVA - INTERNAL - GM USE ONLY", results[0].label)

        results = LookupService.lookup(workflow, "AllTheNames", "uva", limit=10)
        self.assertEquals(1, len(results), "case does not matter.")
        self.assertEquals("UVA - INTERNAL - GM USE ONLY", results[0].label)

        results = LookupService.lookup(workflow, "AllTheNames", "medici", limit=10)
        self.assertEquals(1, len(results), "partial words are picked up.")
        self.assertEquals("The Medicines Company", results[0].label)

        results = LookupService.lookup(workflow, "AllTheNames", "Genetics Savings", limit=10)
        self.assertEquals(1, len(results), "multiple terms are picked up..")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = LookupService.lookup(workflow, "AllTheNames", "Genetics Sav", limit=10)
        self.assertEquals(1, len(results), "prefix queries still work with partial terms")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = LookupService.lookup(workflow, "AllTheNames", "Gen Sav", limit=10)
        self.assertEquals(1, len(results), "prefix queries still work with ALL the partial terms")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = LookupService.lookup(workflow, "AllTheNames", "Inc", limit=10)
        self.assertEquals(7, len(results), "short terms get multiple correct results.")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = LookupService.lookup(workflow, "AllTheNames", "reaction design", limit=10)
        self.assertEquals(5, len(results), "all results come back for two terms.")
        self.assertEquals("Reaction Design", results[0].label, "Exact matches come first.")

        results = LookupService.lookup(workflow, "AllTheNames", "1 Something", limit=10)
        self.assertEquals("1 Something", results[0].label, "Exact matches are prefered")

        results = LookupService.lookup(workflow, "AllTheNames", "1 (!-Something", limit=10)
        self.assertEquals("1 Something", results[0].label, "special characters don't flake out")



# 1018	10000 Something	Industry
# 1019	1000 Something	Industry
# 1020	1 Something	Industry
# 1021	10 Something	Industry
# 1022	10000 Something	Industry

        # Fixme:  Stop words are taken into account on the query side, and haven't found a fix yet.
        #results = WorkflowService.run_lookup_query(lookup_table.id, "in", limit=10)
        #self.assertEquals(7, len(results), "stop words are not removed.")
        #self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)


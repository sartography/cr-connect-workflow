import os
from time import sleep

from tests.base_test import BaseTest

from crc.api.common import ApiError
from crc import session, app
from crc.models.file import DocumentModel, LookupFileModel, LookupDataModel
from crc.services.lookup_service import LookupService
from crc.services.spec_file_service import SpecFileService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.document_service import DocumentService


class TestLookupService(BaseTest):

    def test_lookup_returns_good_error_on_bad_field(self):
        spec = self.load_test_spec('enum_options_with_search')
        workflow = self.create_workflow('enum_options_with_search')
        file_model = session.query(DocumentModel).filter(DocumentModel.name == "customer_list.xlsx").first()
        with self.assertRaises(ApiError):
            LookupService.lookup(workflow, "Task_Enum_Lookup", "not_the_right_field", "sam", limit=10)

    def test_lookup_table_is_not_created_more_than_once(self):
        spec = self.load_test_spec('enum_options_with_search')
        workflow = self.create_workflow('enum_options_with_search')
        self.assertEqual(0, session.query(LookupFileModel).count())
        LookupService.lookup(workflow, "Task_Enum_Lookup", "sponsor", "sam", limit=10)
        self.assertEqual(1, session.query(LookupFileModel).count())
        lookup_table_orig = session.query(LookupFileModel).first()
        LookupService.lookup(workflow, "Task_Enum_Lookup", "sponsor", "something", limit=10)
        lookup_table = session.query(LookupFileModel).first()
        self.assertEqual(lookup_table_orig, lookup_table, f"Lookup models should be the same, and have the same dates:"
                                                          f"{lookup_table_orig.file_timestamp} "
                                                          f"and {lookup_table.file_timestamp} ")
        LookupService.lookup(workflow, "Task_Enum_Lookup", "sponsor", "blah", limit=10)
        lookup_records = session.query(LookupFileModel).all()
        self.assertIsNotNone(lookup_records)
        self.assertEqual(1, len(lookup_records))
        lookup_record = lookup_records[0]
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_record).all()
        self.assertEqual(28, len(lookup_data))

    def test_updates_to_file_cause_lookup_rebuild(self):
        spec = self.load_test_spec('enum_options_with_search')
        workflow = self.create_workflow('enum_options_with_search')
        LookupService.lookup(workflow, "Task_Enum_Lookup", "sponsor", "sam", limit=10)
        lookup_records = session.query(LookupFileModel).all()
        self.assertIsNotNone(lookup_records)
        self.assertEqual(1, len(lookup_records))
        lookup_record = lookup_records[0]
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_record).all()
        self.assertEqual(28, len(lookup_data))

        sleep(1)
        # Update the workflow specification file.
        file_path = os.path.join(app.root_path, '..', 'tests', 'data',
                                 'enum_options_with_search', 'sponsors_modified.xlsx')
        file = open(file_path, 'rb')
        workflow_spec_model = self.workflow_spec_service.get_spec(workflow.workflow_spec_id)
        SpecFileService().update_file(workflow_spec_model, "sponsors.xlsx", file.read())
        file.close()

        # restart the workflow, so it can pick up the changes.
        WorkflowProcessor.reset(workflow)
        processor = WorkflowProcessor(workflow)
        workflow = processor.workflow_model

        LookupService.lookup(workflow, "Task_Enum_Lookup", "sponsor", "sam", limit=10)
        lookup_records = session.query(LookupFileModel).all()
        lookup_record = lookup_records[0]
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_record).all()
        self.assertEqual(4, len(lookup_data))

    def test_lookup_based_on_id(self):
        spec = self.load_test_spec('enum_options_from_file')
        workflow = self.create_workflow('enum_options_from_file')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "", value="1000", limit=10)
        self.assertEqual(1, len(results), "It is possible to find an item based on the id, rather than as a search")
        self.assertIsNotNone(results[0])
        self.assertIsInstance(results[0], dict)


    def test_lookup_with_two_spreadsheets_with_the_same_field_name_in_different_forms(self):
        spec = self.load_test_spec('enum_options_competing_files')
        workflow = self.create_workflow('enum_options_competing_files')
        processor = WorkflowProcessor(workflow)

        processor.do_engine_steps()
        task = processor.get_ready_user_tasks()[0]
        task.data = {"type": "animals"}
        processor.complete_task(task)
        processor.do_engine_steps()
        task = processor.get_ready_user_tasks()[0]
        results = LookupService.lookup(workflow, task.task_spec.name, "selectedItem", "", value="pigs", limit=10)
        self.assertEqual(1, len(results), "It is possible to find an item based on the id, rather than as a search")
        self.assertIsNotNone(results[0])
        results = LookupService.lookup(workflow, task.task_spec.name, "selectedItem", "", value="apples", limit=10)
        self.assertEqual(0, len(results), "We shouldn't find our fruits mixed in with our animals.")

        WorkflowProcessor.reset(workflow, clear_data=True)
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.get_ready_user_tasks()[0]
        task.data = {"type": "fruits"}
        processor.complete_task(task)
        processor.do_engine_steps()
        task = processor.get_ready_user_tasks()[0]
        results = LookupService.lookup(workflow, task.task_spec.name, "selectedItem", "", value="apples", limit=10)
        self.assertEqual(1, len(results), "It is possible to find an item based on the id, rather than as a search")
        self.assertIsNotNone(results[0])
        results = LookupService.lookup(workflow, task.task_spec.name, "selectedItem", "", value="pigs", limit=10)
        self.assertEqual(0, len(results), "We shouldn't find our animals mixed in with our fruits.")


    def test_some_full_text_queries(self):
        spec = self.load_test_spec('enum_options_from_file')
        workflow = self.create_workflow('enum_options_from_file')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "", limit=10)
        self.assertEqual(10, len(results), "Blank queries return everything, to the limit")

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "medicines", limit=10)
        self.assertEqual(1, len(results), "words in the middle of label are detected.")
        self.assertEqual("The Medicines Company", results[0]['CUSTOMER_NAME'])

        results = LookupService.lookup(workflow,"TaskEnumLookup", "AllTheNames", "UVA", limit=10)
        self.assertEqual(1, len(results), "Beginning of label is found.")
        self.assertEqual("UVA - INTERNAL - GM USE ONLY", results[0]['CUSTOMER_NAME'])

        results = LookupService.lookup(workflow, "TaskEnumLookup","AllTheNames", "uva", limit=10)
        self.assertEqual(1, len(results), "case does not matter.")
        self.assertEqual("UVA - INTERNAL - GM USE ONLY", results[0]['CUSTOMER_NAME'])

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "medici", limit=10)
        self.assertEqual(1, len(results), "partial words are picked up.")
        self.assertEqual("The Medicines Company", results[0]['CUSTOMER_NAME'])

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "Genetics Savings", limit=10)
        self.assertEqual(1, len(results), "multiple terms are picked up..")
        self.assertEqual("Genetics Savings & Clone, Inc.", results[0]['CUSTOMER_NAME'])

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "Genetics Sav", limit=10)
        self.assertEqual(1, len(results), "prefix queries still work with partial terms")
        self.assertEqual("Genetics Savings & Clone, Inc.", results[0]['CUSTOMER_NAME'])

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "Gen Sav", limit=10)
        self.assertEqual(1, len(results), "prefix queries still work with ALL the partial terms")
        self.assertEqual("Genetics Savings & Clone, Inc.", results[0]['CUSTOMER_NAME'])

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "Inc", limit=10)
        self.assertEqual(7, len(results), "short terms get multiple correct results.")
        self.assertEqual("Genetics Savings & Clone, Inc.", results[0]['CUSTOMER_NAME'])

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "reaction design", limit=10)
        self.assertEqual(3, len(results), "all results come back for two terms.")
        self.assertEqual("Reaction Design", results[0]['CUSTOMER_NAME'], "Exact matches come first.")

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "1 Something", limit=10)
        self.assertEqual("1 Something", results[0]['CUSTOMER_NAME'], "Exact matches are preferred")

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "1 (!-Something", limit=10)
        self.assertEqual("1 Something", results[0]['CUSTOMER_NAME'], "special characters don't flake out")

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "1  Something", limit=10)
        self.assertEqual("1 Something", results[0]['CUSTOMER_NAME'], "double spaces should not be an issue.")

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "in", limit=10)
        self.assertEqual(10, len(results), "stop words are not removed.")
        self.assertEqual("Genetics Savings & Clone, Inc.", results[0]['CUSTOMER_NAME'])

        results = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", "other", limit=10)
        self.assertEqual("Other", results[0]['CUSTOMER_NAME'], "Can't find the word 'other', which is an english stop word")

    def test_find_by_id(self):
        spec = self.load_test_spec('enum_options_from_file')
        workflow = self.create_workflow('enum_options_from_file')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        result = LookupService.lookup(workflow, "TaskEnumLookup", "AllTheNames", None, value="1000")
        first_result = result[0]
        self.assertEquals(1000, first_result['CUSTOMER_NUMBER'])
        self.assertEquals('UVA - INTERNAL - GM USE ONLY', first_result['CUSTOMER_NAME'])

    def test_lookup_fails_for_xls(self):
        spec = self.load_test_spec('enum_options_with_search')

        # Using an old xls file should raise an error
        file_data_xls = SpecFileService().get_data(spec, 'sponsors.xls')
        timestamp = SpecFileService().timestamp(spec, 'sponsors.xls')
        with self.assertRaises(ApiError) as ae:
            LookupService.build_lookup_table('sponsors.xls', file_data_xls, timestamp, 'CUSTOMER_NUMBER', 'CUSTOMER_NAME')
        self.assertIn('Error opening excel file', ae.exception.args[0])

        # Using an xlsx file should work
        file_data_xlsx = SpecFileService().get_data(spec, 'sponsors.xlsx')
        timestamp = SpecFileService().timestamp(spec, 'sponsors.xlsx')
        lookup_model = LookupService.build_lookup_table('sponsors.xlsx', file_data_xlsx, timestamp,
                                                        'CUSTOMER_NUMBER', 'CUSTOMER_NAME')
        self.assertEqual(28, len(lookup_model.dependencies))
        self.assertIn('CUSTOMER_NAME', lookup_model.dependencies[0].data.keys())
        self.assertIn('CUSTOMER_NUMBER', lookup_model.dependencies[0].data.keys())

    def test_lookup_for_reference_caches_properly(self):
        self.create_reference_document()
        lookup_model_1 = LookupService.get_lookup_model_for_reference(DocumentService.DOCUMENT_LIST,
                                                                      'code', 'description')
        lookup_model_2 = LookupService.get_lookup_model_for_reference(DocumentService.DOCUMENT_LIST,
                                                                      'code', 'description')
        self.assertEqual(lookup_model_1, lookup_model_2)
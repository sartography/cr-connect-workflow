from crc import session
from crc.models.file import FileDataModel, FileModel, LookupFileModel, LookupDataModel
from crc.services.file_service import FileService
from crc.services.lookup_service import LookupService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from tests.base_test import BaseTest


class TestLookupService(BaseTest):

    def test_create_lookup_file_multiple_times_does_not_update_database(self):
        spec = self.load_test_spec('enum_options_from_file')
        file_model = session.query(FileModel).filter(FileModel.name == "customer_list.xls").first()
        file_data_model = session.query(FileDataModel).filter(FileDataModel.file_model == file_model).first()
        LookupService.get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NUMBER", "CUSTOMER_NAME")
        LookupService.get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NUMBER", "CUSTOMER_NAME")
        LookupService.get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NUMBER", "CUSTOMER_NAME")
        lookup_records = session.query(LookupFileModel).all()
        self.assertIsNotNone(lookup_records)
        self.assertEqual(1, len(lookup_records))
        lookup_record = lookup_records[0]
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_record).all()
        self.assertEquals(19, len(lookup_data))
        # Using the same table with different lookup lable or value, does create additional records.
        LookupService.get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NAME", "CUSTOMER_NUMBER")
        lookup_records = session.query(LookupFileModel).all()
        self.assertIsNotNone(lookup_records)
        self.assertEqual(2, len(lookup_records))
        FileService.delete_file(file_model.id) ## Assure we can delete the file.

    def test_some_full_text_queries(self):
        self.load_test_spec('enum_options_from_file')
        file_model = session.query(FileModel).filter(FileModel.name == "customer_list.xls").first()
        self.assertIsNotNone(file_model)
        file_data_model = session.query(FileDataModel).filter(FileDataModel.file_model == file_model).first()
        lookup_table = LookupService.get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NUMBER", "CUSTOMER_NAME")

        results = LookupService._run_lookup_query(lookup_table, "medicines", limit=10)
        self.assertEquals(1, len(results), "words in the middle of label are detected.")
        self.assertEquals("The Medicines Company", results[0].label)

        results = LookupService._run_lookup_query(lookup_table, "", limit=10)
        self.assertEquals(10, len(results), "Blank queries return everything, to the limit")

        results = LookupService._run_lookup_query(lookup_table, "UVA", limit=10)
        self.assertEquals(1, len(results), "Beginning of label is found.")
        self.assertEquals("UVA - INTERNAL - GM USE ONLY", results[0].label)

        results = LookupService._run_lookup_query(lookup_table, "uva", limit=10)
        self.assertEquals(1, len(results), "case does not matter.")
        self.assertEquals("UVA - INTERNAL - GM USE ONLY", results[0].label)



        results = LookupService._run_lookup_query(lookup_table, "medici", limit=10)
        self.assertEquals(1, len(results), "partial words are picked up.")
        self.assertEquals("The Medicines Company", results[0].label)

        results = LookupService._run_lookup_query(lookup_table, "Genetics Savings", limit=10)
        self.assertEquals(1, len(results), "multiple terms are picked up..")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = LookupService._run_lookup_query(lookup_table, "Genetics Sav", limit=10)
        self.assertEquals(1, len(results), "prefix queries still work with partial terms")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = LookupService._run_lookup_query(lookup_table, "Gen Sav", limit=10)
        self.assertEquals(1, len(results), "prefix queries still work with ALL the partial terms")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = LookupService._run_lookup_query(lookup_table, "Inc", limit=10)
        self.assertEquals(7, len(results), "short terms get multiple correct results.")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        # Fixme:  Stop words are taken into account on the query side, and haven't found a fix yet.
        #results = WorkflowService.run_lookup_query(lookup_table.id, "in", limit=10)
        #self.assertEquals(7, len(results), "stop words are not removed.")
        #self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

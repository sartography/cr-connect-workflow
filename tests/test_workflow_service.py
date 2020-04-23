import json
import os

from sqlalchemy import func

from crc import session, app
from crc.models.api_models import WorkflowApiSchema, Task
from crc.models.file import FileModelSchema, FileDataModel, FileModel, LookupFileModel, LookupDataModel
from crc.models.stats import WorkflowStatsModel, TaskEventModel
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from tests.base_test import BaseTest


class TestWorkflowService(BaseTest):

    def test_documentation_processing_handles_replacements(self):
        self.load_example_data()
        workflow = self.create_workflow('random_fact')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        task = processor.next_task()
        task.task_spec.documentation = "Some simple docs"
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("Some simple docs", docs)

        task.data = {"replace_me": "new_thing"}
        task.task_spec.documentation = "{{replace_me}}"
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("new_thing", docs)

        documentation = """
# Bigger Test

  * bullet one
  * bullet two has {{replace_me}}

# other stuff.       
        """
        expected = """
# Bigger Test

  * bullet one
  * bullet two has new_thing

# other stuff.       
        """
        task.task_spec.documentation = documentation
        result = WorkflowService._process_documentation(task)
        self.assertEqual(expected, result)

    def test_documentation_processing_handles_conditionals(self):

        self.load_example_data()
        workflow = self.create_workflow('random_fact')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        task = processor.next_task()
        task.task_spec.documentation = "This test {% if works == 'yes' %}works{% endif %}"
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("This test ", docs)

        task.data = {"works": 'yes'}
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("This test works", docs)

    def test_enum_options_from_file(self):
        self.load_example_data()
        workflow = self.create_workflow('enum_options_from_file')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        WorkflowService.process_options(task, task.task_spec.form.fields[0])
        options = task.task_spec.form.fields[0].options
        self.assertEquals(19, len(options))
        self.assertEquals('1000', options[0]['id'])
        self.assertEquals("UVA - INTERNAL - GM USE ONLY", options[0]['name'])

    def test_create_lookup_file(self):
        spec = self.load_test_spec('enum_options_from_file')
        file_model = session.query(FileModel).filter(FileModel.name == "customer_list.xls").first()
        file_data_model = session.query(FileDataModel).filter(FileDataModel.file_model == file_model).first()
        WorkflowService._get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NUMBER", "CUSTOMER_NAME")
        lookup_records = session.query(LookupFileModel).all()
        self.assertIsNotNone(lookup_records)
        self.assertEqual(1, len(lookup_records))
        lookup_record = lookup_records[0]
        self.assertIsNotNone(lookup_record)
        self.assertEquals("CUSTOMER_NUMBER", lookup_record.value_column)
        self.assertEquals("CUSTOMER_NAME", lookup_record.label_column)
        self.assertEquals("CUSTOMER_NAME", lookup_record.label_column)
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_record).all()
        self.assertEquals(19, len(lookup_data))

        self.assertEquals("1000", lookup_data[0].value)
        self.assertEquals("UVA - INTERNAL - GM USE ONLY", lookup_data[0].label)
        # search_results = session.query(LookupDataModel).\
        #     filter(LookupDataModel.lookup_file_model_id == lookup_record.id).\
        #     filter(LookupDataModel.__ts_vector__.op('@@')(func.plainto_tsquery('INTERNAL'))).all()
        search_results = LookupDataModel.query.filter(LookupDataModel.label.match("INTERNAL")).all()
        self.assertEquals(1, len(search_results))
        search_results = LookupDataModel.query.filter(LookupDataModel.label.match("internal")).all()
        self.assertEquals(1, len(search_results))
        # This query finds results where a word starts with "bio"
        search_results = LookupDataModel.query.filter(LookupDataModel.label.match("bio:*")).all()
        self.assertEquals(2, len(search_results))

    def test_create_lookup_file_multiple_times_does_not_update_database(self):
        spec = self.load_test_spec('enum_options_from_file')
        file_model = session.query(FileModel).filter(FileModel.name == "customer_list.xls").first()
        file_data_model = session.query(FileDataModel).filter(FileDataModel.file_model == file_model).first()
        WorkflowService._get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NUMBER", "CUSTOMER_NAME")
        WorkflowService._get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NUMBER", "CUSTOMER_NAME")
        WorkflowService._get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NUMBER", "CUSTOMER_NAME")
        lookup_records = session.query(LookupFileModel).all()
        self.assertIsNotNone(lookup_records)
        self.assertEqual(1, len(lookup_records))
        lookup_record = lookup_records[0]
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_record).all()
        self.assertEquals(19, len(lookup_data))
        # Using the same table with different lookup lable or value, does create additional records.
        WorkflowService._get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NAME", "CUSTOMER_NUMBER")
        lookup_records = session.query(LookupFileModel).all()
        self.assertIsNotNone(lookup_records)
        self.assertEqual(2, len(lookup_records))

    def test_some_full_text_queries(self):
        self.load_test_spec('enum_options_from_file')
        file_model = session.query(FileModel).filter(FileModel.name == "customer_list.xls").first()
        file_data_model = session.query(FileDataModel).filter(FileDataModel.file_model == file_model).first()
        lookup_table = WorkflowService._get_lookup_table_from_data_model(file_data_model, "CUSTOMER_NUMBER", "CUSTOMER_NAME")
        lookup_data = session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_table).all()

        results = WorkflowService.run_lookup_query(lookup_table.id, "medicines", limit=10)
        self.assertEquals(1, len(results), "words in the middle of label are detected.")
        self.assertEquals("The Medicines Company", results[0].label)

        results = WorkflowService.run_lookup_query(lookup_table.id, "", limit=10)
        self.assertEquals(10, len(results), "Blank queries return everything, to the limit")

        results = WorkflowService.run_lookup_query(lookup_table.id, "UVA", limit=10)
        self.assertEquals(1, len(results), "Beginning of label is found.")
        self.assertEquals("UVA - INTERNAL - GM USE ONLY", results[0].label)

        results = WorkflowService.run_lookup_query(lookup_table.id, "uva", limit=10)
        self.assertEquals(1, len(results), "case does not matter.")
        self.assertEquals("UVA - INTERNAL - GM USE ONLY", results[0].label)



        results = WorkflowService.run_lookup_query(lookup_table.id, "medici", limit=10)
        self.assertEquals(1, len(results), "partial words are picked up.")
        self.assertEquals("The Medicines Company", results[0].label)

        results = WorkflowService.run_lookup_query(lookup_table.id, "Genetics Savings", limit=10)
        self.assertEquals(1, len(results), "multiple terms are picked up..")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = WorkflowService.run_lookup_query(lookup_table.id, "Genetics Sav", limit=10)
        self.assertEquals(1, len(results), "prefix queries still work with partial terms")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = WorkflowService.run_lookup_query(lookup_table.id, "Gen Sav", limit=10)
        self.assertEquals(1, len(results), "prefix queries still work with ALL the partial terms")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        results = WorkflowService.run_lookup_query(lookup_table.id, "Inc", limit=10)
        self.assertEquals(7, len(results), "short terms get multiple correct results.")
        self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

        # Fixme:  Stop words are taken into account on the query side, and haven't found a fix yet.
        #results = WorkflowService.run_lookup_query(lookup_table.id, "in", limit=10)
        #self.assertEquals(7, len(results), "stop words are not removed.")
        #self.assertEquals("Genetics Savings & Clone, Inc.", results[0].label)

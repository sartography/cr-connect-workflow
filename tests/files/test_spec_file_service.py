import datetime

from github import UnknownObjectException
from sqlalchemy import desc, column
from tests.base_test import BaseTest
from unittest.mock import patch, Mock

from crc import db, session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES, FileType
from crc.services.spec_file_service import SpecFileService
from crc.services.workflow_processor import WorkflowProcessor



class TestSpecFileService(BaseTest):

    def test_get_spec_files(self):
        self.load_example_data()
        spec = self.load_test_spec("random_fact")
        spec_files = SpecFileService().get_files(spec)
        self.assertEqual(2, len(spec_files))
        spec_files = SpecFileService().get_files(spec, "random_fact.bpmn")
        self.assertEqual(1, len(spec_files))
        self.assertEqual("text/xml", spec_files[0].content_type)
        self.assertEqual("random_fact.bpmn", spec_files[0].name)
        self.assertTrue(spec_files[0].size > 0)
        self.assertEqual(FileType.bpmn, spec_files[0].type)
        self.assertIsInstance(spec_files[0].last_modified, datetime.datetime)

    def test_add_file(self):
        self.load_example_data()
        spec_random = self.load_test_spec("random_fact")
        spec_dt = self.load_test_spec("decision_table")
        data = SpecFileService.get_data(spec_random, "random_fact.bpmn")
        self.assertIsNotNone(data)
        spec_files = SpecFileService().get_files(spec_dt)
        self.assertEqual(0, len(SpecFileService().get_files(spec_dt, "random_fact.bpmn")))
        SpecFileService.add_file(spec_dt, "random_fact.bpmn", data)
        self.assertEqual(1, len(SpecFileService().get_files(spec_dt, "random_fact.bpmn")))

        orig = SpecFileService.get_files(spec_random, "random_fact.bpmn")[0]
        new = SpecFileService.get_files(spec_dt, "random_fact.bpmn")[0]
        self.assertEqual(orig.size, new.size)
        # This next line happens too fast now, so we can't verify the dates are different
        #self.assertNotEqual(orig.last_modified, new.last_modified)

    def test_set_primary_bpmn(self):
        self.load_example_data()
        spec_random = self.load_test_spec("random_fact")
        SpecFileService.set_primary_bpmn(spec_random, 'random_fact.bpmn')
        self.assertEquals('random_fact.bpmn', spec_random.primary_file_name)
        self.assertEquals('Process_1ds61df', spec_random.primary_process_id)
        SpecFileService.set_primary_bpmn(spec_random, 'random_fact2.bpmn')
        self.assertEquals('random_fact2.bpmn', spec_random.primary_file_name)
        self.assertEquals('Process_SecondFact', spec_random.primary_process_id)

    def test_delete_workflow_spec_file(self):
        self.load_example_data()
        spec = self.load_test_spec("random_fact")
        spec_files = SpecFileService.get_files(spec)
        self.assertEqual(2, len(spec_files))
        SpecFileService.delete_file(spec, "random_fact2.bpmn")
        spec_files = SpecFileService.get_files(spec)
        self.assertEqual(1, len(spec_files))


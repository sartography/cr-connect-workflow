import unittest

from SpiffWorkflow import Workflow
from SpiffWorkflow.serializer.json import JSONSerializer
from SpiffWorkflow.specs import WorkflowSpec

from app.model.task.strike import NuclearSerializer
from tests.base_test import BaseTest


class TestWorkflow(BaseTest, unittest.TestCase):

    def test_truthyness(self):
        self.assertTrue(True)

    def test_404(self):
        response = self.app.get('/some/endpoint')
        self.assertEquals(404, response.status_code)

    def test_all_workflows_api_endpoint(self):
        response = self.app.get('/v1.0/workflows')
        response_data = response.json
        self.assertEqual('Full IRB Board Review',response_data[0]['name'])

    def load_spec_from_file(self, path):
        with open(path) as fp:
            workflow_json = fp.read()
        serializer = NuclearSerializer()
        spec = WorkflowSpec.deserialize(serializer, workflow_json)
        return spec

    def test_workflow_from_file(self):
        spec = self.load_spec_from_file('../app/static/json/nuclear.json')
        self.assertIsNotNone(spec)

    def test_workflow_from_spec(self):
        spec = self.load_spec_from_file('../app/static/json/nuclear.json')
        workflow = Workflow(spec)
        self.assertIsNotNone(spec)
        print("=======================")
        print(workflow.dump())
        workflow.complete_all(halt_on_manual=True)
        print("=======================")
        print(workflow.dump())
        print("=======================")



    def test_open_bpmn_diagram(self):
        self.assertTrue(False, "Test loading a simple bpmn diagram")


import json
import unittest

from SpiffWorkflow import Workflow
from SpiffWorkflow.bpmn.serializer.BpmnSerializer import BpmnSerializer
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.serializer.json import JSONSerializer
from SpiffWorkflow.specs import WorkflowSpec

from app.camunda.WorkflowRunner import BPMNXMLWorkflowRunner
from app.model.WorkflowRunner import WorkflowRunner
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

    def load_spec_from_json(self, path):
        with open(path) as fp:
            workflow_json = fp.read()
        serializer = NuclearSerializer()
        spec = WorkflowSpec.deserialize(serializer, workflow_json)
        return spec

    def load_spec_from_bpmn(self, path):
        with open(path) as fp:
            serializer = BpmnSerializer()
            spec = WorkflowSpec.deserialize(serializer, fp)
        return spec


    def test_workflow_from_file(self):
        spec = self.load_spec_from_json('../app/static/json/nuclear.json')
        self.assertIsNotNone(spec)

    def test_workflow_from_spec(self):
        spec = self.load_spec_from_json('../app/static/json/nuclear.json')
        workflow = Workflow(spec)
        self.assertIsNotNone(spec)
        print("=======================")
        print(workflow.dump())
        workflow.complete_all(halt_on_manual=True)
        print("=======================")
        print(workflow.dump())
        print("=======================")



    def test_open_bpmn_diagram(self):
        runner = BPMNXMLWorkflowRunner('../app/static/bpmn/joke.bpmn', debug=True)
        runner.start(x=1)
        res = runner.getEndEventName()
        self.assertEqual(res, 'Task_1u241z0')

    def test_loading_joke(self):
        runner = WorkflowRunner('../app/static/bpmn/joke.bpmn', debug=True)
        spec = runner.get_spec()
        workflow = BpmnWorkflow(spec)

        workflow.debug = False
        serializer = JSONSerializer()
        data = workflow.serialize(serializer)
        pretty = json.dumps(json.loads(data), indent=4, separators=(',', ': '))
        print("=======================")
        print(pretty)
        print("=======================")



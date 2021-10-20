from tests.base_test import BaseTest
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService

from crc import mail

import json


class TestJinjaService(BaseTest):

    def test_jinja_service_documentation(self):
        self.load_example_data()
        workflow = self.create_workflow('random_fact')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        task = processor.next_task()
        task.data = {"my_template": "Hi {{name}}, This is a jinja template too!",
                     "name": "Dan"}
        task.task_spec.documentation = """{% include 'my_template' %} Cool Right?"""
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("Hi Dan, This is a jinja template too! Cool Right?", docs)

    def test_jinja_service_email(self):
        workflow = self.create_workflow('jinja_email')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        data = {'subject': "My Email Subject",
                'recipients': 'user@example.com',
                'include_me': "Hello {{name}}, This is a jinja template too!",
                'name': 'World'}

        with mail.record_messages() as outbox:
            workflow_api = self.complete_form(workflow, task, data)

            self.assertIn('Hello World, This is a jinja template too!', outbox[0].body)
            self.assertIn("# Email Model", workflow_api.next_task.documentation)
            self.assertIn("My Email Subject", workflow_api.next_task.documentation)
            self.assertIn("user@example.com", workflow_api.next_task.documentation)

            print(f'test_jinja_service_email: {workflow_api.next_task.data}')

    def test_jinja_service_tools(self):
        template = "This is my template. {% include 'include_me' %} Was something included?"
        data = {"name": "World",
                "include_me": "Hello {{name}}!"}
        rv = self.app.get('/v1.0/render_markdown?template=%s&data=%s' %
                          (template, json.dumps(data)))
        self.assert_success(rv)
        self.assertIn("Hello World", rv.get_data(as_text=True))

    def test_jinja_service_documents(self):
        pass

    def test_jinja_service_properties(self):
        pass

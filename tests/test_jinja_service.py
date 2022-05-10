import os
from io import BytesIO

from tests.base_test import BaseTest
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from crc.services.jinja_service import JinjaService
from flask_bpmn.api.common import ApiError

from crc import mail, app

import json


class TestJinjaService(BaseTest):

    def test_jinja_service_element_documentation(self):

        workflow = self.create_workflow('random_fact')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        task = processor.next_task()
        task.data = {"my_template": "Hi {{name}}, This is a jinja template too!",
                     "name": "Dan"}
        task.task_spec.documentation = """{% include 'my_template' %} Cool Right?"""
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("Hi Dan, This is a jinja template too! Cool Right?", docs)

    def test_jinja_service_included_includes(self):
        """This is an obnoxious test for nested includes.
           Also tests for multiple includes within a single template"""
        workflow = self.create_workflow('random_fact')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        task = processor.next_task()
        data = {"my_template": "Hi {% include 'my_name_template' %} from {% include 'my_org_template' %},\n{% include 'my_content_template' %}",
                "my_name_template": "{{name}}",
                "my_org_template": "{{org}}",
                "my_content_template": "This is an included {% include 'my_jinja_template' %} template too!",
                "my_jinja_template": "Jinja",
                "name": "Dan",
                "org": "Bucky's"}
        task.data = data
        task.task_spec.documentation = """This is an included template:\n {% include 'my_template' %} \nCool Right?"""
        docs = WorkflowService._process_documentation(task)

        self.assertEqual('This is an included template:\n Hi Dan from Bucky\'s,\nThis is an included Jinja template too! \nCool Right?', docs)

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

    def test_jinja_service_tools_markdown(self):
        template = "This is my template. {% include 'include_me' %} Was something included?"
        data = {"name": "World",
                "include_me": "Hello {{name}}!"}
        rv = self.app.get('/v1.0/render_markdown?template=%s&data=%s' %
                          (template, json.dumps(data)))
        self.assert_success(rv)
        self.assertIn("Hello World", rv.get_data(as_text=True))

    def test_jinja_service_word_documents(self):
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', 'template.docx')
        with open(filepath, 'rb') as myfile:
            file_data = BytesIO(myfile.read())
        context = {'title': 'My Title', 'my_list': ["a", "b", "c"], 'show_table': True}
        result = JinjaService().make_template(file_data, context)
        self.assertIsNotNone(result)  # Not a lot we can do here, just assure there is not an error.

    def test_jinja_service_word_document_errors_are_sensible(self):
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', 'template_error.docx')
        with open(filepath, 'rb') as myfile:
            file_data = BytesIO(myfile.read())
        context = {'title': 'My Title', 'my_list': ["a", "b", "c"], 'show_table': True}
        with self.assertRaises(ApiError) as ae:
            result = JinjaService().make_template(file_data, context)
        self.assertIn('{{% no_such_variable_error ! @ __ %}}', ae.exception.error_line)
        self.assertEquals("Word Document creation error : unexpected '%'", ae.exception.message)
        self.assertEquals(14, ae.exception.line_number)

    def test_find_template_references(self):
        test_string = """
        { % include 'template_1' %}

        { % include
        'template_2' %}

        { % include 'template_3' -%}
        {% include 'template_4'%}

        """
        self.assertEqual(['template_1', 'template_2', 'template_3', 'template_4'], JinjaService().template_references(test_string))

    def test_better_error_message_for_wordwrap(self):
        data = {"my_val": None}
        my_tempate = "{{my_val | wordwrap(70)}}"
        with self.assertRaises(ApiError) as e:
            result = JinjaService().get_content(my_tempate, data)
        self.assertEqual(e.exception.message, 'Error processing template.  You may be using a wordwrap '
                                              'with a field that has no value.')

    def test_jinja_service_properties(self):
        pass

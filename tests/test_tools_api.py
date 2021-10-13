import json
import os

from tests.base_test import BaseTest
from crc import app, mail


class TestToolsApi(BaseTest):

    def test_render_markdown(self):
        template = "My name is {{name}}"
        data = {"name": "Dan"}
        rv = self.app.get('/v1.0/render_markdown?template=%s&data=%s' %
                          (template, json.dumps(data)))
        self.assert_success(rv)
        self.assertEqual("My name is Dan", rv.get_data(as_text=True))

    def test_render_docx(self):
        filepath = os.path.join(app.root_path, '..', 'tests', 'data', 'table.docx')
        template_data = {"hippa": [
                   {"option": "Name", "selected": True, "stored": ["Record at UVA", "Stored Long Term"]},
                   {"option": "Address", "selected": False},
                   {"option": "Phone", "selected": True, "stored": ["Send or Transmit outside of UVA"]}]}
        with open(filepath, 'rb') as f:
            file_data = {'file': (f, 'my_new_file.bpmn'), 'data': json.dumps(template_data)}
            rv = self.app.put('/v1.0/render_docx',
                              data=file_data, follow_redirects=True,
                              content_type='multipart/form-data')
            self.assert_success(rv)
            self.assertIsNotNone(rv.data)
            self.assertEqual('application/octet-stream', rv.content_type)

    def test_list_scripts(self):
        rv = self.app.get('/v1.0/list_scripts')
        self.assert_success(rv)
        scripts = json.loads(rv.get_data(as_text=True))
        self.assertTrue(len(scripts) > 1)
        self.assertIsNotNone(scripts[0]['name'])
        self.assertIsNotNone(scripts[0]['handle'])
        self.assertIsNotNone(scripts[0]['description'])

    def test_eval_hide_expression(self):
        """Assures we can use python to process a hide expression from the front end"""
        rv = self.app.put('/v1.0/eval',
                          data='{"expression": "x.y==2", "data": {"x":{"y":2}}, "key": 1234}', follow_redirects=True,
                          content_type='application/json',
                          headers=self.logged_in_headers())
        self.assert_success(rv)
        response = json.loads(rv.get_data(as_text=True))
        self.assertEqual(True, response['result'])

    def test_eval_returns_query(self):
        """Assures that along with the result, we get the key and expression.
        This can be useful if the calling client is caching results and needs to hash the expression and data
        when it gets returned."""
        data = '{"expression": "x.y==2", "data": {"x":{"y":2}}, "key":1234}'
        rv = self.app.put('/v1.0/eval',
                          data=data, follow_redirects=True,
                          content_type='application/json',
                          headers=self.logged_in_headers())
        self.assert_success(rv)
        response = json.loads(rv.get_data(as_text=True))
        self.assertEqual("x.y==2", response['expression'])
        self.assertEqual(1234, response['key'])


    def test_eval_expression_with_strings(self):
        """Assures we can use python to process a value expression from the front end"""
        rv = self.app.put('/v1.0/eval',
                          data='{"expression": "\'Hello, \' + user.first_name + \' \' + user.last_name + \'!!!\'", '
                               '"data": {"user":{"first_name": "Trillian", "last_name": "Astra"}},'
                               '"key":1234}',
                          follow_redirects=True,
                          content_type='application/json',
                          headers=self.logged_in_headers())
        self.assert_success(rv)
        response = json.loads(rv.get_data(as_text=True))
        self.assertEqual('Hello, Trillian Astra!!!', response['result'])

    def test_send_email(self):
        subject = 'CR Connect Test Email'
        address = 'user@example.com'
        data = {'user': 'Person of Interest'}
        message = """
Dear {{ user }},

Thank you for using this email example.
I hope this makes sense.

Yours faithfully,
CR Connect
"""
        with mail.record_messages() as outbox:
            rv = self.app.put('/v1.0/send_email?subject=%s&address=%s&data=%s' %
                              (subject, address, json.dumps(data)), data=json.dumps(message), headers=self.logged_in_headers())
            self.assert_success(rv)
            self.assertEqual(1, len(outbox))
            self.assertEqual(subject, outbox[0].subject)
            self.assertEqual(['user@example.com'], outbox[0].recipients)
            self.assertIn('Person of Interest', outbox[0].body)

    def test_eval_to_boolean_expression_with_dot_notation(self):
        """Assures we can use python to process a value expression from the front end"""
        rv = self.app.put('/v1.0/eval',
                          data='{"expression": "test.value", "data": {"test":{"value": true}}, "key": 1234}',
                          follow_redirects=True,
                          content_type='application/json',
                          headers=self.logged_in_headers())
        self.assert_success(rv)
        response = json.loads(rv.get_data(as_text=True))
        self.assertEqual(True, response['result'])

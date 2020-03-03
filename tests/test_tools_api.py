import json
import os
from datetime import datetime, timezone

from crc import session, app
from crc.models.study import StudyModel, StudyModelSchema
from crc.models.protocol_builder import ProtocolBuilderStatus
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus, \
    WorkflowApiSchema
from tests.base_test import BaseTest


class TestStudyApi(BaseTest):

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
            file_data = {'file': (f, 'my_new_file.bpmn')}
            rv = self.app.put('/v1.0/render_docx?data=%s' % json.dumps(template_data),
                              data=file_data, follow_redirects=True,
                              content_type='multipart/form-data')
            self.assert_success(rv)

    def test_list_scripts(self):
        rv = self.app.get('/v1.0/list_scripts')
        self.assert_success(rv)
        scripts = json.loads(rv.get_data(as_text=True))
        self.assertTrue(len(scripts) > 1)
        self.assertIsNotNone(scripts[0]['name'])
        self.assertIsNotNone(scripts[0]['description'])

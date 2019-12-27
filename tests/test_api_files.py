import io
import json
import unittest
from datetime import datetime

from crc import db
from crc.models import WorkflowSpecModel, FileModel, FileType, FileSchema
from tests.base_test import BaseTest


class TestApiFiles(BaseTest, unittest.TestCase):

    def test_list_files_for_workflow_spec(self):
        self.load_example_data()
        spec = db.session.query(WorkflowSpecModel).first()
        rv = self.app.get('/v1.0/file?spec_id=%s' % spec.id,
                          follow_redirects=True,
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(1, len(json_data))
        file = FileSchema(many=True).load(json_data, session=db.session)
        self.assertEqual("random_fact.bpmn", file[0].name)

    def test_list_multiple_files_for_workflow_spec(self):
        self.load_example_data()
        spec = db.session.query(WorkflowSpecModel).first()
        svgFile = FileModel(name="test.svg", type=FileType.svg, version=1, last_updated=datetime.now(),
                            primary=False, workflow_spec_id=spec.id)
        db.session.add(svgFile)
        db.session.flush()
        rv = self.app.get('/v1.0/file?spec_id=%s' % spec.id,
                          follow_redirects=True,
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(2, len(json_data))

    def test_create_file(self):
        self.load_example_data()
        spec = db.session.query(WorkflowSpecModel).first()

        data = {'workflow_spec_id': spec.id}
        data['file'] = io.BytesIO(b"abcdef"), 'random_fact.svg'

        rv = self.app.post('/v1.0/file', data=data, follow_redirects=True,
                                   content_type='multipart/form-data')

        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileSchema().load(json_data, session=db.session)
        self.assertEqual(1, file.version)
        self.assertEqual(FileType.svg, file.type)
        self.assertFalse(file.primary)
        self.assertEqual("image/svg+xml", file.content_type)
        self.assertEqual(spec.id, file.workflow_spec_id)

        rv = self.app.get('/v1.0/file/%i' % file.id)
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        file2 = FileSchema().load(json_data, session=db.session)
        self.assertEqual(file, file2)

    def test_update_file(self):
        self.load_example_data()
        spec = db.session.query(WorkflowSpecModel).first()
        file = db.session.query(FileModel).filter_by(workflow_spec_id = spec.id).first()

        data = {}
        data['file'] = io.BytesIO(b"abcdef"), 'random_fact.bpmn'

        rv = self.app.put('/v1.0/file/%i' % file.id, data=data, follow_redirects=True,
                              content_type='multipart/form-data')

        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileSchema().load(json_data, session=db.session)
        self.assertEqual(2, file.version)
        self.assertEqual(FileType.bpmn, file.type)
        self.assertTrue(file.primary)
        self.assertEqual("application/octet-stream", file.content_type)
        self.assertEqual(spec.id, file.workflow_spec_id)

    def test_get_file(self):
        self.load_example_data()
        spec = db.session.query(WorkflowSpecModel).first()
        file = db.session.query(FileModel).filter_by(workflow_spec_id=spec.id).first()
        rv = self.app.get('/v1.0/file/%i/data' % file.id)
        self.assert_success(rv)
        self.assertEquals("application/octet-stream", rv.content_type)
        self.assertTrue(rv.content_length > 1)

    def test_delete_file(self):
        self.load_example_data()
        spec = db.session.query(WorkflowSpecModel).first()
        file = db.session.query(FileModel).filter_by(workflow_spec_id=spec.id).first()
        rv = self.app.get('/v1.0/file/%i' % file.id)
        self.assert_success(rv)
        rv = self.app.delete('/v1.0/file/%i' % file.id)
        rv = self.app.get('/v1.0/file/%i' % file.id)
        self.assertEqual(404, rv.status_code)


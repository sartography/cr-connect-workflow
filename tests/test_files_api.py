import io
import json
from datetime import datetime

from crc import session
from crc.models.file import FileModel, FileType, FileModelSchema, FileDataModel
from crc.models.workflow import WorkflowSpecModel
from tests.base_test import BaseTest


class TestFilesApi(BaseTest):

    def test_list_files_for_workflow_spec(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        rv = self.app.get('/v1.0/file?workflow_spec_id=%s' % spec.id,
                          follow_redirects=True,
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(1, len(json_data))
        file = FileModelSchema(many=True).load(json_data, session=session)
        self.assertEqual("%s.bpmn" % spec.name, file[0].name)

    def test_list_multiple_files_for_workflow_spec(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        svgFile = FileModel(name="test.svg", type=FileType.svg, version=1, last_updated=datetime.now(),
                            primary=False, workflow_spec_id=spec.id)
        session.add(svgFile)
        session.flush()
        rv = self.app.get('/v1.0/file?workflow_spec_id=%s' % spec.id,
                          follow_redirects=True,
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(2, len(json_data))

    def test_create_file(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data')

        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(1, file.version)
        self.assertEqual(FileType.svg, file.type)
        self.assertFalse(file.primary)
        self.assertEqual("image/svg+xml", file.content_type)
        self.assertEqual(spec.id, file.workflow_spec_id)

        rv = self.app.get('/v1.0/file/%i' % file.id)
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        file2 = FileModelSchema().load(json_data, session=session)
        self.assertEqual(file, file2)

    def test_update_file_info(self):
        self.load_example_data()
        file: FileModel = session.query(FileModel).first()
        file.name = "silly_new_name.bpmn"

        rv = self.app.put('/v1.0/file/%i' % file.id,
                           content_type="application/json",
                           data=json.dumps(FileModelSchema().dump(file)))
        self.assert_success(rv)
        db_file = session.query(FileModel).filter_by(id=file.id).first()
        self.assertIsNotNone(db_file)
        self.assertEqual(file.name, db_file.name)

    def test_update_file_data(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {}
        data['file'] = io.BytesIO(b"abcdef"), 'my_new_file.bpmn'
        rv = self.app.post('/v1.0/file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data')
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)

        data['file'] = io.BytesIO(b"hijklim"), 'my_new_file.bpmn'
        rv = self.app.put('/v1.0/file/%i/data' % file.id, data=data, follow_redirects=True,
                          content_type='multipart/form-data')
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(2, file.version)
        self.assertEqual(FileType.bpmn, file.type)
        self.assertEqual("application/octet-stream", file.content_type)
        self.assertEqual(spec.id, file.workflow_spec_id)

        data_model = session.query(FileDataModel).filter_by(file_model_id=file.id).first()
        self.assertEqual(b"hijklim", data_model.data)

    def test_get_file(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        file = session.query(FileModel).filter_by(workflow_spec_id=spec.id).first()
        rv = self.app.get('/v1.0/file/%i/data' % file.id)
        self.assert_success(rv)
        self.assertEqual("text/xml; charset=utf-8", rv.content_type)
        self.assertTrue(rv.content_length > 1)

    def test_delete_file(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        file = session.query(FileModel).filter_by(workflow_spec_id=spec.id).first()
        rv = self.app.get('/v1.0/file/%i' % file.id)
        self.assert_success(rv)
        rv = self.app.delete('/v1.0/file/%i' % file.id)
        rv = self.app.get('/v1.0/file/%i' % file.id)
        self.assertEqual(404, rv.status_code)

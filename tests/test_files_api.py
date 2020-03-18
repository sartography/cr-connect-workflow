import io
import json

from crc import session
from crc.models.file import FileModel, FileType, FileModelSchema
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
        svgFile = FileModel(name="test.svg", type=FileType.svg,
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
        self.assertEqual(FileType.svg, file.type)
        self.assertFalse(file.primary)
        self.assertEqual("image/svg+xml", file.content_type)
        self.assertEqual(spec.id, file.workflow_spec_id)

        rv = self.app.get('/v1.0/file/%i' % file.id)
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        file2 = FileModelSchema().load(json_data, session=session)
        self.assertEqual(file, file2)

    def test_set_reference_file(self):
        file_name = "irb_document_types.xls"
        data = {'file': (io.BytesIO(b"abcdef"), "does_not_matter.xls")}
        rv = self.app.put('/v1.0/reference_file/%s' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data')
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(FileType.xls, file.type)
        self.assertTrue(file.is_reference)
        self.assertEqual("application/vnd.ms-excel", file.content_type)

    def test_set_reference_file_bad_extension(self):
        file_name = "irb_document_types.xls"
        data = {'file': (io.BytesIO(b"abcdef"), "does_not_matter.ppt")}
        rv = self.app.put('/v1.0/reference_file/%s' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data')
        self.assert_failure(rv, error_code="invalid_file_type")

    def test_get_reference_file(self):
        file_name = "irb_document_types.xls"
        data = {'file': (io.BytesIO(b"abcdef"), "some crazy thing do not care.xls")}
        rv = self.app.put('/v1.0/reference_file/%s' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data')
        rv = self.app.get('/v1.0/reference_file/%s' % file_name)
        self.assert_success(rv)
        data_out = rv.get_data()
        self.assertEqual(b"abcdef", data_out)

    def test_list_reference_files(self):
        file_name = "irb_document_types.xls"
        data = {'file': (io.BytesIO(b"abcdef"), file_name)}
        rv = self.app.put('/v1.0/reference_file/%s' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data')

        rv = self.app.get('/v1.0/reference_file',
                          follow_redirects=True,
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(1, len(json_data))
        file = FileModelSchema(many=True).load(json_data, session=session)
        self.assertEqual(file_name, file[0].name)
        self.assertTrue(file[0].is_reference)

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
        self.assertEqual(2, file.latest_version)
        self.assertEqual(FileType.bpmn, file.type)
        self.assertEqual("application/octet-stream", file.content_type)
        self.assertEqual(spec.id, file.workflow_spec_id)

        rv = self.app.get('/v1.0/file/%i/data' % file.id)
        self.assert_success(rv)
        data = rv.get_data()
        self.assertIsNotNone(data)
        self.assertEqual(b"hijklim", data)

    def test_update_with_same_exact_data_does_not_increment_version(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {}
        data['file'] = io.BytesIO(b"abcdef"), 'my_new_file.bpmn'
        rv = self.app.post('/v1.0/file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data')
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(1, file.latest_version)
        data['file'] = io.BytesIO(b"abcdef"), 'my_new_file.bpmn'
        rv = self.app.put('/v1.0/file/%i/data' % file.id, data=data, follow_redirects=True,
                          content_type='multipart/form-data')
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(1, file.latest_version)

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


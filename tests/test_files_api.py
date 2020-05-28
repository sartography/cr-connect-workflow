import io
import json

from tests.base_test import BaseTest

from crc import session
from crc.models.file import FileModel, FileType, FileModelSchema, FileDataModel
from crc.models.workflow import WorkflowSpecModel
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor
from example_data import ExampleDataLoader


class TestFilesApi(BaseTest):

    def minimal_bpmn(self, content):
        """Returns a bytesIO object of a well formed BPMN xml file with some string content of your choosing."""
        minimal_dbpm = "<x><process id='1' isExecutable='false'><startEvent id='a'/></process>%s</x>"
        return (minimal_dbpm % content).encode()

    def test_list_files_for_workflow_spec(self):
        self.load_example_data(use_crc_data=True)
        spec_id = 'core_info'
        spec = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()
        rv = self.app.get('/v1.0/file?workflow_spec_id=%s' % spec_id,
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(5, len(json_data))
        files = FileModelSchema(many=True).load(json_data, session=session)
        file_names = [f.name for f in files]
        self.assertTrue("%s.bpmn" % spec.name in file_names)

    def test_list_multiple_files_for_workflow_spec(self):
        self.load_example_data()
        spec = self.load_test_spec("random_fact")
        svgFile = FileModel(name="test.svg", type=FileType.svg,
                            primary=False, workflow_spec_id=spec.id)
        session.add(svgFile)
        session.flush()
        rv = self.app.get('/v1.0/file?workflow_spec_id=%s' % spec.id,
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(2, len(json_data))

    def test_create_file(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())

        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(FileType.svg, file.type)
        self.assertFalse(file.primary)
        self.assertEqual("image/svg+xml", file.content_type)
        self.assertEqual(spec.id, file.workflow_spec_id)

        rv = self.app.get('/v1.0/file/%i' % file.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        file2 = FileModelSchema().load(json_data, session=session)
        self.assertEqual(file, file2)

    def test_add_file_from_task_and_form_errors_on_invalid_form_field_name(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        correct_name = task.task_spec.form.fields[0].id

        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_id=%i&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.id, "not_a_known_file"), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_failure(rv, error_code="invalid_form_field_key")

        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_id=%i&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.id, correct_name), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)


    def test_set_reference_file(self):
        file_name = "irb_document_types.xls"
        data = {'file': (io.BytesIO(b"abcdef"), "does_not_matter.xls")}
        rv = self.app.put('/v1.0/reference_file/%s' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(FileType.xls, file.type)
        self.assertTrue(file.is_reference)
        self.assertEqual("application/vnd.ms-excel", file.content_type)

    def test_set_reference_file_bad_extension(self):
        file_name = FileService.DOCUMENT_LIST
        data = {'file': (io.BytesIO(b"abcdef"), "does_not_matter.ppt")}
        rv = self.app.put('/v1.0/reference_file/%s' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_failure(rv, error_code="invalid_file_type")

    def test_get_reference_file(self):
        file_name = "irb_document_types.xls"
        data = {'file': (io.BytesIO(b"abcdef"), "some crazy thing do not care.xls")}
        rv = self.app.put('/v1.0/reference_file/%s' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        rv = self.app.get('/v1.0/reference_file/%s' % file_name, headers=self.logged_in_headers())
        self.assert_success(rv)
        data_out = rv.get_data()
        self.assertEqual(b"abcdef", data_out)

    def test_list_reference_files(self):
        ExampleDataLoader.clean_db()

        file_name = FileService.DOCUMENT_LIST
        data = {'file': (io.BytesIO(b"abcdef"), file_name)}
        rv = self.app.put('/v1.0/reference_file/%s' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())

        rv = self.app.get('/v1.0/reference_file',
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
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
                           data=json.dumps(FileModelSchema().dump(file)), headers=self.logged_in_headers())
        self.assert_success(rv)
        db_file = session.query(FileModel).filter_by(id=file.id).first()
        self.assertIsNotNone(db_file)
        self.assertEqual(file.name, db_file.name)

    def test_update_file_data(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'
        rv = self.app.post('/v1.0/file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)

        data['file'] = io.BytesIO(self.minimal_bpmn("efghijk")), 'my_new_file.bpmn'
        rv = self.app.put('/v1.0/file/%i/data' % file.id, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(2, file.latest_version)
        self.assertEqual(FileType.bpmn, file.type)
        self.assertEqual("application/octet-stream", file.content_type)
        self.assertEqual(spec.id, file.workflow_spec_id)

        # Assure it is updated in the database and properly persisted.
        file_model = session.query(FileModel).filter(FileModel.id == file.id).first()
        self.assertEqual(2, file_model.latest_version)

        rv = self.app.get('/v1.0/file/%i/data' % file.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        data = rv.get_data()
        self.assertIsNotNone(data)
        self.assertEqual(self.minimal_bpmn("efghijk"), data)

    def test_update_with_same_exact_data_does_not_increment_version(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'
        rv = self.app.post('/v1.0/file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(1, file.latest_version)
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'
        rv = self.app.put('/v1.0/file/%i/data' % file.id, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(1, file.latest_version)

    def test_get_file(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        file = session.query(FileModel).filter_by(workflow_spec_id=spec.id).first()
        rv = self.app.get('/v1.0/file/%i/data' % file.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertEqual("text/xml; charset=utf-8", rv.content_type)
        self.assertTrue(rv.content_length > 1)

    def test_delete_file(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        file = session.query(FileModel).filter_by(workflow_spec_id=spec.id).first()
        rv = self.app.get('/v1.0/file/%i' % file.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        rv = self.app.delete('/v1.0/file/%i' % file.id, headers=self.logged_in_headers())
        rv = self.app.get('/v1.0/file/%i' % file.id, headers=self.logged_in_headers())
        self.assertEqual(404, rv.status_code)

    def test_change_primary_bpmn(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'

        # Add a new BPMN file to the specification
        rv = self.app.post('/v1.0/file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)

        # Delete the primary BPMN file for the workflow.
        orig_model = session.query(FileModel).\
            filter(FileModel.primary == True).\
            filter(FileModel.workflow_spec_id == spec.id).first()
        rv = self.app.delete('/v1.0/file?file_id=%s' % orig_model.id, headers=self.logged_in_headers())


        # Set that new file to be the primary BPMN, assure it has a primary_process_id
        file.primary = True
        rv = self.app.put('/v1.0/file/%i' % file.id,
                           content_type="application/json",
                           data=json.dumps(FileModelSchema().dump(file)), headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertTrue(json_data['primary'])
        self.assertIsNotNone(json_data['primary_process_id'])


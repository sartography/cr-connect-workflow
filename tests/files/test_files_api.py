import io
import json
import os

from tests.base_test import BaseTest

from crc import session, db, app
from crc.models.file import FileModel, FileType, FileModelSchema
from crc.models.workflow import WorkflowSpecModel
from crc.services.file_service import FileService
from crc.services.spec_file_service import SpecFileService
from crc.services.workflow_processor import WorkflowProcessor
from crc.models.data_store import DataStoreModel
from crc.services.document_service import DocumentService
from example_data import ExampleDataLoader

from sqlalchemy import column


class TestFilesApi(BaseTest):

    def test_list_files_for_workflow_spec(self):
        self.load_example_data(use_crc_data=True)
        spec_id = 'core_info'
        spec = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()
        rv = self.app.get('/v1.0/spec_file?workflow_spec_id=%s' % spec_id,
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(5, len(json_data))
        files = FileModelSchema(many=True).load(json_data, session=session)
        file_names = [f.name for f in files]
        self.assertTrue("%s.bpmn" % spec.id in file_names)

    def  btest_list_multiple_files_for_workflow_spec(self):
        self.load_example_data()
        spec = self.load_test_spec("random_fact")
        data = {'file': (io.BytesIO(b"abcdef"), 'test.svg')}
        self.app.post('/v1.0/spec_file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                      content_type='multipart/form-data', headers=self.logged_in_headers())
        rv = self.app.get('/v1.0/spec_file?workflow_spec_id=%s' % spec.id,
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(3, len(json_data))

    def test_create_spec_file(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/spec_file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
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
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        correct_name = task.task_spec.form.fields[0].id

        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.get_name(), correct_name), data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)

    def test_archive_file_no_longer_shows_up(self):
        self.load_example_data()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        correct_name = task.task_spec.form.fields[0].id

        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.get_name(), correct_name), data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())

        self.assert_success(rv)
        rv = self.app.get('/v1.0/file?workflow_id=%s' % workflow.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertEqual(1, len(json.loads(rv.get_data(as_text=True))))

        file_model = db.session.query(FileModel).filter(FileModel.workflow_id == workflow.id).all()
        self.assertEqual(1, len(file_model))
        file_model[0].archived = True
        db.session.commit()

        rv = self.app.get('/v1.0/file?workflow_id=%s' % workflow.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertEqual(0, len(json.loads(rv.get_data(as_text=True))))

    def test_update_reference_file_data(self):
        self.load_example_data()
        file_name = "documents.xlsx"
        filepath = os.path.join(app.root_path, 'static', 'reference', 'irb_documents.xlsx')
        with open(filepath, 'rb') as myfile:
            file_data = myfile.read()
        data = {'file': (io.BytesIO(file_data), file_name)}
        rv = self.app.put('/v1.0/reference_file/%s/data' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(FileType.xlsx, file.type)
        self.assertTrue(file.is_reference)
        self.assertEqual("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", file.content_type)
        # self.assertEqual('dhf8r', json_data['user_uid'])

    def test_set_reference_file_bad_extension(self):
        file_name = DocumentService.DOCUMENT_LIST
        data = {'file': (io.BytesIO(b"abcdef"), "does_not_matter.ppt")}
        rv = self.app.put('/v1.0/reference_file/%s/data' % file_name, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_failure(rv, error_code="invalid_file_type")

    def test_get_reference_file_data(self):
        ExampleDataLoader().load_reference_documents()
        file_name = "irb_document_types.xls"
        filepath = os.path.join(app.root_path, 'static', 'reference', 'irb_documents.xlsx')
        with open(filepath, 'rb') as f_open:
            file_data = f_open.read()
        data = {'file': (io.BytesIO(file_data), file_name)}
        self.app.post('/v1.0/reference_file', data=data, follow_redirects=True,
                      content_type='multipart/form-data', headers=self.logged_in_headers())
        rv = self.app.get('/v1.0/reference_file/%s/data' % file_name, headers=self.logged_in_headers())
        self.assert_success(rv)
        data_out = rv.get_data()
        self.assertEqual(file_data, data_out)

    def test_get_reference_file_info(self):
        self.load_example_data()
        reference_file_model = session.query(FileModel).filter(FileModel.is_reference==True).first()
        name = reference_file_model.name
        rv = self.app.get('/v1.0/reference_file/%s' % name, headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))

        self.assertEqual(reference_file_model.name, json_data['name'])
        self.assertEqual(reference_file_model.type.value, json_data['type'])
        self.assertEqual(reference_file_model.id, json_data['id'])

    def test_add_reference_file(self):
        ExampleDataLoader().load_reference_documents()

        file_name = 'new.xlsx'
        data = {'file': (io.BytesIO(b"abcdef"), file_name)}
        rv = self.app.post('/v1.0/reference_file', data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)
        self.assertEqual(FileType.xlsx, file.type)
        self.assertFalse(file.primary)
        self.assertEqual(True, file.is_reference)

    def test_delete_reference_file(self):
        ExampleDataLoader().load_reference_documents()
        reference_file = session.query(FileModel).filter(FileModel.is_reference == True).first()
        rv = self.app.get('/v1.0/reference_file/%s' % reference_file.name, headers=self.logged_in_headers())
        self.assert_success(rv)
        self.app.delete('/v1.0/reference_file/%s' % reference_file.name, headers=self.logged_in_headers())
        db.session.flush()
        rv = self.app.get('/v1.0/reference_file/%s' % reference_file.name, headers=self.logged_in_headers())
        self.assertEqual(404, rv.status_code)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertIn('The reference file name you provided', json_data['message'])

    def test_list_reference_files(self):
        ExampleDataLoader.clean_db()

        file_name = DocumentService.DOCUMENT_LIST
        filepath = os.path.join(app.root_path, 'static', 'reference', 'irb_documents.xlsx')
        with open(filepath, 'rb') as myfile:
            file_data = myfile.read()
        data = {'file': (io.BytesIO(file_data), file_name)}
        rv = self.app.post('/v1.0/reference_file', data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
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
        file: FileModel = session.query(FileModel).filter(column('workflow_spec_id').isnot(None)).first()
        file_model = FileModel(id=file.id,
                               name="silly_new_name.bpmn",
                               type=file.type,
                               content_type=file.content_type,
                               is_reference=file.is_reference,
                               primary=file.primary,
                               primary_process_id=file.primary_process_id,
                               workflow_id=file.workflow_id,
                               workflow_spec_id=file.workflow_spec_id,
                               archived=file.archived)
        # file.name = "silly_new_name.bpmn"

        rv = self.app.put('/v1.0/spec_file/%i' % file.id,
                          content_type="application/json",
                          data=json.dumps(FileModelSchema().dump(file_model)), headers=self.logged_in_headers())
        self.assert_success(rv)
        db_file = session.query(FileModel).filter_by(id=file.id).first()
        self.assertIsNotNone(db_file)
        self.assertEqual("silly_new_name.bpmn", db_file.name)

    def test_load_valid_url_for_files(self):
        self.load_example_data()
        file: FileModel = session.query(FileModel).filter(FileModel.is_reference == False).first()
        rv = self.app.get('/v1.0/file/%i' % file.id, content_type="application/json", headers=self.logged_in_headers())
        self.assert_success(rv)
        file_json = json.loads(rv.get_data(as_text=True))
        print(file_json)
        self.assertIsNotNone(file_json['url'])
        file_data_rv = self.app.get(file_json['url'])
        self.assert_success(file_data_rv)

    def test_update_file_data(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'
        rv_1 = self.app.post('/v1.0/spec_file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                             content_type='multipart/form-data', headers=self.logged_in_headers())
        file_json_1 = json.loads(rv_1.get_data(as_text=True))
        self.assertEqual(80, file_json_1['size'])

        file_id = file_json_1['id']
        rv_2 = self.app.get('/v1.0/spec_file/%i/data' % file_id, headers=self.logged_in_headers())
        self.assert_success(rv_2)
        rv_data_2 = rv_2.get_data()
        self.assertIsNotNone(rv_data_2)
        self.assertEqual(self.minimal_bpmn("abcdef"), rv_data_2)

        data['file'] = io.BytesIO(self.minimal_bpmn("efghijk")), 'my_new_file.bpmn'
        rv_3 = self.app.put('/v1.0/spec_file/%i/data' % file_id, data=data, follow_redirects=True,
                            content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv_3)
        self.assertIsNotNone(rv_3.get_data())
        file_json_3 = json.loads(rv_3.get_data(as_text=True))
        self.assertEqual(FileType.bpmn.value, file_json_3['type'])
        self.assertEqual("application/octet-stream", file_json_3['content_type'])
        self.assertEqual(spec.id, file_json_3['workflow_spec_id'])

        # Assure it is updated in the database and properly persisted.
        file_model = session.query(FileModel).filter(FileModel.id == file_id).first()
        file_data = SpecFileService().get_spec_file_data(file_model.id)
        self.assertEqual(81, len(file_data.data))

        rv_4 = self.app.get('/v1.0/spec_file/%i/data' % file_id, headers=self.logged_in_headers())
        self.assert_success(rv_4)
        data = rv_4.get_data()
        self.assertIsNotNone(data)
        self.assertEqual(self.minimal_bpmn("efghijk"), data)

    def test_get_file(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        file = session.query(FileModel).filter_by(workflow_spec_id=spec.id).first()
        rv = self.app.get('/v1.0/spec_file/%i/data' % file.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertEqual("text/xml; charset=utf-8", rv.content_type)
        self.assertTrue(rv.content_length > 1)

    def test_get_file_contains_data_store_elements(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        file = session.query(FileModel).filter_by(workflow_spec_id=spec.id).first()
        ds = DataStoreModel(key="my_key", value="my_value", file_id=file.id);
        db.session.add(ds)
        rv = self.app.get('/v1.0/file/%i' % file.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual("my_value", json_data['data_store']['my_key'])

    def test_get_files_for_form_field_returns_only_those_files(self):
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        correct_name = task.task_spec.form.fields[0].id

        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.get_name(), correct_name), data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)

        # Note:  this call can be made WITHOUT the task id.
        rv = self.app.get('/v1.0/file?study_id=%i&workflow_id=%s&form_field_key=%s' %
                          (workflow.study_id, workflow.id, correct_name), follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(len(json_data), 1)

        # Add another file for a different document type
        FileService().add_workflow_file(workflow.id, 'Study_App_Doc', task.get_name(), 'otherdoc.docx',
                                        'application/xcode', b"asdfasdf")

        # Note:  this call can be made WITHOUT the task spec name.
        rv = self.app.get('/v1.0/file?study_id=%i&workflow_id=%s&form_field_key=%s' %
                          (workflow.study_id, workflow.id, correct_name), follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(len(json_data), 1)

    def test_add_file_returns_document_metadata(self):
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form_single')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        correct_name = task.task_spec.form.fields[0].id

        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, task.get_name(), correct_name), data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual('Ancillary Document', json_data['document']['category1'])
        self.assertEqual('Study Team', json_data['document']['who_uploads?'])

    def test_delete_spec_file(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        file = session.query(FileModel).filter_by(workflow_spec_id=spec.id).first()
        file_id = file.id
        rv = self.app.get('/v1.0/spec_file/%i' % file.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        self.app.delete('/v1.0/spec_file/%i' % file.id, headers=self.logged_in_headers())
        db.session.flush()
        rv = self.app.get('/v1.0/spec_file/%i' % file_id, headers=self.logged_in_headers())
        self.assertEqual(404, rv.status_code)

    def test_change_primary_bpmn(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'

        # Add a new BPMN file to the specification
        rv = self.app.post('/v1.0/spec_file?workflow_spec_id=%s' % spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)

        # Delete the primary BPMN file for the workflow.
        orig_model = session.query(FileModel). \
            filter(FileModel.primary == True). \
            filter(FileModel.workflow_spec_id == spec.id).first()
        rv = self.app.delete('/v1.0/spec_file?file_id=%s' % orig_model.id, headers=self.logged_in_headers())

        # Set that new file to be the primary BPMN, assure it has a primary_process_id
        file.primary = True
        rv = self.app.put('/v1.0/spec_file/%i' % file.id,
                          content_type="application/json",
                          data=json.dumps(FileModelSchema().dump(file)), headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertTrue(json_data['primary'])
        self.assertIsNotNone(json_data['primary_process_id'])

    def test_file_upload_with_previous_name(self):
        self.load_example_data()
        workflow_spec_model = session.query(WorkflowSpecModel).first()

        # Add file
        data = {'file': (io.BytesIO(b'asdf'), 'test_file.xlsx')}
        rv = self.app.post('/v1.0/spec_file?workflow_spec_id=%s' % workflow_spec_model.id,
                           data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data',
                           headers=self.logged_in_headers())

        self.assert_success(rv)
        file_json = json.loads(rv.get_data(as_text=True))
        file_id = file_json['id']

        # Set file to archived
        file_model = session.query(FileModel).filter_by(id=file_id).first()
        file_model.archived = True
        session.commit()

        # Assert we have the correct file data and the file is archived
        file_data_model = SpecFileService().get_spec_file_data(file_model.id)
        self.assertEqual(b'asdf', file_data_model.data)
        file_model = session.query(FileModel).filter_by(id=file_model.id).first()
        self.assertEqual(True, file_model.archived)

        # Upload file with same name
        data = {'file': (io.BytesIO(b'xyzpdq'), 'test_file.xlsx')}
        rv = self.app.post('/v1.0/spec_file?workflow_spec_id=%s' % workflow_spec_model.id,
                           data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data',
                           headers=self.logged_in_headers())

        self.assert_success(rv)
        file_json = json.loads(rv.get_data(as_text=True))
        file_id = file_json['id']

        # Assert we have the correct file data and the file is *not* archived
        file_data_model = SpecFileService().get_spec_file_data(file_id)
        self.assertEqual(b'xyzpdq', file_data_model.data)
        file_model = session.query(FileModel).filter_by(id=file_id).first()
        self.assertEqual(False, file_model.archived)

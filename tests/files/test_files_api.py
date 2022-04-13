import io
import json
import os

from tests.base_test import BaseTest

from crc import session, db, app
from crc.models.file import FileType, FileModelSchema
from crc.services.workflow_processor import WorkflowProcessor
from crc.models.data_store import DataStoreModel
from crc.services.document_service import DocumentService
from example_data import ExampleDataLoader
from crc.services.user_file_service import UserFileService


class TestFilesApi(BaseTest):

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

    def test_update_reference_file_data(self):
        file_name = "documents.xlsx"
        filepath = os.path.join(app.root_path, 'static', 'reference', 'documents.xlsx')
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
        filepath = os.path.join(app.root_path, 'static', 'reference', 'documents.xlsx')
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
        self.create_reference_document()
        rv = self.app.get('/v1.0/reference_file/documents.xlsx', headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))

        self.assertEqual("documents.xlsx", json_data['name'])
        self.assertEqual("xlsx", json_data['type'])

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

    def test_delete_reference_file(self):
        ExampleDataLoader().load_reference_documents()
        name = "documents.xlsx"
        rv = self.app.get('/v1.0/reference_file/%s' % name, headers=self.logged_in_headers())
        self.assert_success(rv)
        self.app.delete('/v1.0/reference_file/%s' % name, headers=self.logged_in_headers())
        db.session.flush()
        rv = self.app.get('/v1.0/reference_file/%s' % name, headers=self.logged_in_headers())
        self.assertEqual(404, rv.status_code)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertIn('No reference file found with the name documents.xlsx', json_data['message'])

    def test_list_reference_files(self):
        ExampleDataLoader.clean_db()
        file_name = DocumentService.DOCUMENT_LIST
        filepath = os.path.join(app.root_path, 'static', 'reference', 'documents.xlsx')
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

    def create_user_file(self):
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
        return json.loads(rv.get_data(as_text=True))

    def test_load_valid_url_for_files(self):
        file = self.create_user_file()
        rv = self.app.get('/v1.0/file/%i' % file['id'], content_type="application/json", headers=self.logged_in_headers())
        self.assert_success(rv)
        file_json = json.loads(rv.get_data(as_text=True))
        print(file_json)
        self.assertIsNotNone(file_json['url'])
        file_data_rv = self.app.get(file_json['url'])
        self.assert_success(file_data_rv)

    def test_get_file_contains_data_store_elements(self):
        file = self.create_user_file()
        ds = DataStoreModel(key="my_key", value="my_value", file_id=file['id'])
        db.session.add(ds)
        rv = self.app.get('/v1.0/file/%i' % file['id'], headers=self.logged_in_headers())
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
        UserFileService().add_workflow_file(workflow.id, 'Study_App_Doc', task.get_name(), 'otherdoc.docx',
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


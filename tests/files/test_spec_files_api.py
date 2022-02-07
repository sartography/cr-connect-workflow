import io
import json
import os

from tests.base_test import BaseTest

from crc import session, db, app
from crc.models.file import FileModel, FileType, FileModelSchema
from crc.services.spec_file_service import SpecFileService
from crc.services.workflow_processor import WorkflowProcessor
from crc.models.data_store import DataStoreModel
from crc.services.document_service import DocumentService
from example_data import ExampleDataLoader

from sqlalchemy import column


class TestFilesApi(BaseTest):

    def test_list_files_for_workflow_spec(self):
        self.load_example_data(use_crc_data=True)
        spec_id = 'random_fact'
        spec = self.load_test_spec(spec_id)
        rv = self.app.get('/v1.0/workflow-specification/%s/file' % spec_id,
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(2, len(json_data))
        files = FileModelSchema(many=True).load(json_data, session=session)
        file_names = [f.name for f in files]
        self.assertTrue("%s.bpmn" % spec.id in file_names)

    def test_list_multiple_files_for_workflow_spec(self):
        self.load_example_data()
        spec = self.load_test_spec("random_fact")
        data = {'file': (io.BytesIO(b"abcdef"), 'test.svg')}
        self.app.post('/v1.0/workflow-specification/%s/file' % spec.id, data=data, follow_redirects=True,
                      content_type='multipart/form-data', headers=self.logged_in_headers())
        rv = self.app.get('/v1.0/workflow-specification/%s/file' % spec.id,
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(3, len(json_data))

    def test_create_spec_file(self):
        self.load_example_data()
        spec = self.load_test_spec('random_fact')
        data = {'file': (io.BytesIO(b"abcdef"), 'random_fact.svg')}
        rv = self.app.post('/v1.0/workflow-specification/%s/file' % spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())

        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        file = json.loads(rv.get_data(as_text=True))
        self.assertEqual(FileType.svg.value, file['type'])
        self.assertEqual("image/svg+xml", file['content_type'])

        rv = self.app.get(f'/v1.0/workflow-specification/{spec.id}/file/random_fact.svg', headers=self.logged_in_headers())
        self.assert_success(rv)
        file2 = json.loads(rv.get_data(as_text=True))
        self.assertEqual(file, file2)

    def test_update_spec_file_data(self):
        self.load_example_data()
        spec = self.load_test_spec('random_fact')
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'
        rv_1 = self.app.post('/v1.0/workflow-specification/%s/file' % spec.id, data=data, follow_redirects=True,
                             content_type='multipart/form-data', headers=self.logged_in_headers())
        file_json_1 = json.loads(rv_1.get_data(as_text=True))
        self.assertEqual(80, file_json_1['size'])

        rv_2 = self.app.get(f'/v1.0/workflow-specification/{spec.id}/file/my_new_file.bpmn/data',
                            headers=self.logged_in_headers())
        self.assert_success(rv_2)
        rv_data_2 = rv_2.get_data()
        self.assertIsNotNone(rv_data_2)
        self.assertEqual(self.minimal_bpmn("abcdef"), rv_data_2)

        data['file'] = io.BytesIO(self.minimal_bpmn("efghijk")), 'my_new_file.bpmn'
        rv_3 = self.app.put(f'/v1.0/workflow-specification/{spec.id}/file/my_new_file.bpmn/data',
                            data=data, follow_redirects=True,
                            content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv_3)
        self.assertIsNotNone(rv_3.get_data())
        file_json_3 = json.loads(rv_3.get_data(as_text=True))
        self.assertEqual(FileType.bpmn.value, file_json_3['type'])
        self.assertEqual("text/xml", file_json_3['content_type'])

        # Assure it is updated in the database and properly persisted.
        file_data = SpecFileService().get_data(spec, "my_new_file.bpmn")
        self.assertEqual(81, len(file_data))

        rv_4 = self.app.get(f'/v1.0/workflow-specification/{spec.id}/file/my_new_file.bpmn/data',
                            headers=self.logged_in_headers())
        self.assert_success(rv_4)
        data = rv_4.get_data()
        self.assertIsNotNone(data)
        self.assertEqual(self.minimal_bpmn("efghijk"), data)

    def test_get_spec_file(self):
        self.load_example_data()
        spec = self.load_test_spec('random_fact')
        spec = session.query(WorkflowSpecModel).first()
        rv = self.app.get(f'/v1.0/workflow-specification/{spec.id}/file',
                             headers=self.logged_in_headers())
        files = json.loads(rv.get_data(as_text=True))
        rv = self.app.get(f'/v1.0/workflow-specification/{spec.id}/file/{files[0]["name"]}/data',
                          headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertEqual("text/xml; charset=utf-8", rv.content_type)
        self.assertTrue(rv.content_length > 1)

    def test_delete_spec_file(self):
        self.load_example_data()
        spec = self.load_test_spec('random_fact')
        rv = self.app.get(f'/v1.0/workflow-specification/{spec.id}/file/random_fact.bpmn',
                             headers=self.logged_in_headers())
        self.assert_success(rv)
        rv = self.app.delete(f'/v1.0/workflow-specification/{spec.id}/file/random_fact.bpmn',
                             headers=self.logged_in_headers())
        self.assert_success(rv)
        rv = self.app.get(f'/v1.0/workflow-specification/{spec.id}/file/random_fact.bpmn',
                             headers=self.logged_in_headers())
        self.assertEqual(404, rv.status_code)

    def test_change_primary_bpmn(self):
        self.load_example_data()
        spec = self.load_test_spec('random_fact')
        spec = session.query(WorkflowSpecModel).first()
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'

        # Add a new BPMN file to the specification
        rv = self.app.post(f'/v1.0/workflow-specification/{spec.id}/file', data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertIsNotNone(rv.get_data())
        json_data = json.loads(rv.get_data(as_text=True))
        file = FileModelSchema().load(json_data, session=session)

        # get that mf.
        rv = self.app.get(f'/v1.0/workflow-specification/{spec.id}/file/random_fact.bpmn',
                             headers=self.logged_in_headers())
        self.assert_success(rv)


        # Delete the original BPMN file for the workflow.
        rv = self.app.delete(f'/v1.0/workflow-specification/{spec.id}/file/random_fact.bpmn',
                             headers=self.logged_in_headers())
        self.assert_success(rv)

        # Set new file to be the primary BPMN file
        rv = self.app.put(f'/v1.0/workflow-specification/{spec.id}/file/my_new_file.bpmn?is_primary=True',
                          headers=self.logged_in_headers())
        self.assert_success(rv)

        # Get the workflow_spec
        rv = self.app.get(f'/v1.0/workflow-specification/{spec.id}', headers=self.logged_in_headers())
        workflow_spec = json.loads(rv.get_data(as_text=True))
        self.assertEqual('my_new_file.bpmn', workflow_spec['primary_file_name'])
        self.assertIsNotNone(workflow_spec['primary_process_id'])

    def test_file_upload_with_previous_name(self):
        self.load_example_data()
        workflow_spec_model = self.load_test_spec('random_fact')

        # Add file
        data = {'file': (io.BytesIO(b'asdf'), 'test_file.xlsx')}
        rv = self.app.post('/v1.0/workflow-specification/%s/file' % workflow_spec_model.id,
                           data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data',
                           headers=self.logged_in_headers())

        self.assert_success(rv)
        file_json = json.loads(rv.get_data(as_text=True))

        # Assert we have the correct file data
        file_data = SpecFileService().get_data(workflow_spec_model, 'test_file.xlsx')
        self.assertEqual(b'asdf', file_data)

        # Upload file with same name
        data = {'file': (io.BytesIO(b'xyzpdq'), 'test_file.xlsx')}
        rv = self.app.post('/v1.0/workflow-specification/%s/file' % workflow_spec_model.id,
                           data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data',
                           headers=self.logged_in_headers())

        self.assert_success(rv)

        # Assert we have the correct file data
        file_data = SpecFileService().get_data(workflow_spec_model, 'test_file.xlsx')
        self.assertEqual(b'xyzpdq', file_data)

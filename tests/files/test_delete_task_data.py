from tests.base_test import BaseTest

from crc import session

from crc.models.data_store import DataStoreModel
from crc.models.file import DocumentModel
from crc.models.task_event import TaskEventModel
from crc.services.workflow_service import WorkflowService

from io import BytesIO


class TestDeleteTaskData(BaseTest):

    def test_delete_task_data_validation(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        spec_model = self.load_test_spec('delete_task_data')
        self.create_reference_document()
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        # Make sure we don't get json returned. This would indicate an error.
        self.assertEqual([], rv.json)

    def test_delete_task_data(self):
        self.create_reference_document()
        doc_code_1 = 'Study_Protocol_Document'
        doc_code_2 = 'Study_App_Doc'

        workflow = self.create_workflow('delete_task_data')

        # Make sure there are no files uploaded for workflow yet
        files = session.query(DocumentModel).filter(DocumentModel.workflow_id == workflow.id).all()
        self.assertEqual(0, len(files))

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        # Upload Single File
        data = {'file': (BytesIO(b"abcdef"), 'test_file.txt')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, first_task.name, doc_code_1), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_id = rv.json['id']
        self.complete_form(workflow, first_task, {doc_code_1: {'id': file_id},
                                                  'VerDate': '20210721'})

        # Make sure we have 1 file
        files = session.query(DocumentModel).filter(DocumentModel.workflow_id == workflow.id).all()
        self.assertEqual(1, len(files))

        # Make sure data store is set
        data_store = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id).all()
        self.assertEqual('VerDate', data_store[0].key)
        self.assertEqual('20210721', data_store[0].value)

        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task

        # Upload 2 Files
        data = {'file': (BytesIO(b"abcdef"), 'test_file_1.txt')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, first_task.name, doc_code_2), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_id_1 = rv.json['id']
        data = {'file': (BytesIO(b"ghijk"), 'test_file_2.txt')}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&form_field_key=%s' %
                           (workflow.study_id, workflow.id, first_task.name, doc_code_2), data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_id_2 = rv.json['id']

        self.complete_form(workflow, second_task, {'StudyAppDoc': [{'Study_App_Doc': {'id': file_id_1},
                                                                    'VerDate': '20210701',
                                                                    'ShortDesc': 'Short Description 1'},
                                                                   {'Study_App_Doc': {'id': file_id_2},
                                                                    'VerDate': '20210702',
                                                                    'ShortDesc': 'Short Description 2'}
                                                                   ]})

        # Make sure we have 2 more files
        files = session.query(DocumentModel).filter(DocumentModel.workflow_id == workflow.id).all()
        self.assertEqual(3, len(files))

        # Make sure data stores are set for new files
        data_stores_1 = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id_1).all()
        for data_store in data_stores_1:
            if data_store.key == 'VerDate':
                self.assertEqual('20210701', data_store.value)
            elif data_store.key == 'ShortDesc':
                self.assertEqual('Short Description 1', data_store.value)

        data_stores_2 = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id_2).all()
        for data_store in data_stores_2:
            if data_store.key == 'VerDate':
                self.assertEqual('20210702', data_store.value)
            elif data_store.key == 'ShortDesc':
                self.assertEqual('Short Description 2', data_store.value)

        # Make sure we have something in task_events
        task_events = session.query(TaskEventModel).\
            filter(TaskEventModel.workflow_id == workflow.id).\
            filter(TaskEventModel.action == WorkflowService.TASK_ACTION_COMPLETE).all()
        for task_event in task_events:
            self.assertNotEqual({}, task_event.form_data)

        workflow_api = self.get_workflow_api(workflow)
        third_task = workflow_api.next_task
        # This calls the delete task file data script
        self.complete_form(workflow, third_task, {})
        self.get_workflow_api(workflow)

        # Make sure files, data_stores, and task_events are deleted
        data_stores = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id).all()
        data_stores_1 = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id_1).all()
        data_stores_2 = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id_2).all()
        files = session.query(DocumentModel).filter(DocumentModel.workflow_id == workflow.id).all()
        task_events = session.query(TaskEventModel).\
            filter(TaskEventModel.workflow_id == workflow.id).\
            filter(TaskEventModel.action == WorkflowService.TASK_ACTION_COMPLETE).all()

        self.assertEqual(0, len(data_stores))
        self.assertEqual(0, len(data_stores_1))
        self.assertEqual(0, len(data_stores_2))
        self.assertEqual(0, len(files))
        for task_event in task_events:
            self.assertEqual({}, task_event.form_data)
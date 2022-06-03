from tests.base_test import BaseTest

from crc import session
from crc.models.file import FileModel
from crc.services.workflow_processor import WorkflowProcessor

import io
import json


class TestDeleteFile(BaseTest):
    doc_code = 'Study_Protocol_Document'

    def setup_workflows(self):
        # create 2 workflows
        hello_world = self.create_workflow('hello_world')
        simple_form = self.create_workflow('simple_form')

        # add a file to each workflow
        self.upload_document(hello_world, self.doc_code, 'my_file.svg', b'abcde')
        self.upload_document(simple_form, self.doc_code, 'my_other_file.svg', b'lmnop')

        # make sure the files exist and are not archived
        hello_world_files = self.get_files_for_workflow(hello_world)
        simple_form_files = self.get_files_for_workflow(simple_form)

        self.assertEqual(1, len(hello_world_files))
        self.assertEqual(1, len(simple_form_files))
        self.assertFalse(hello_world_files[0].archived)
        self.assertFalse(simple_form_files[0].archived)

        return hello_world, simple_form

    def upload_document(self, workflow, doc_code, file_name, file_data):
        self.create_reference_document()
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()

        data = {'file': (io.BytesIO(file_data), file_name)}
        rv = self.app.post('/v1.0/file?study_id=%i&workflow_id=%s&task_spec_name=%s&irb_doc_code=%s' %
                           (workflow.study_id, workflow.id, task.get_name(), doc_code),
                           data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data',
                           headers=self.logged_in_headers())
        self.assert_success(rv)
        return json.loads(rv.get_data(as_text=True))

    @staticmethod
    def get_files_for_workflow(workflow):
        files = session.query(FileModel) \
            .filter(FileModel.workflow_id == workflow.id).all()
        return files

    def run_delete_file_script(self, form_data):
        # run a workflow that deletes the documents (based on the doc_code)
        workflow = self.create_workflow('delete_file_script')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        self.complete_form(workflow, task, form_data)

    def test_delete_file(self):
        # create 2 workflows; hello_world and simple_form
        # add a file to each workflow
        # make sure the files exist and are not archived
        hello_world, simple_form = self.setup_workflows()

        form_data = {'doc_codes': [self.doc_code]}
        self.run_delete_file_script(form_data)

        # get the files for both workflows
        hello_world_files = self.get_files_for_workflow(hello_world)
        simple_form_files = self.get_files_for_workflow(simple_form)
        self.assertEqual(1, len(hello_world_files))
        self.assertEqual(1, len(simple_form_files))

        # make sure all the files are archived
        self.assertTrue(hello_world_files[0].archived)
        self.assertTrue(simple_form_files[0].archived)

    def test_delete_file_workflow_only(self):
        """This time, we also upload a file to the `delete_file_script` itself.
           When we run the delete file script, we pass `study_wide=False`
           This should only delete files for the current workflow.
           The files for hello_world and simple_form should be unaffected"""
        hello_world, simple_form = self.setup_workflows()

        delete_file_script = self.create_workflow('delete_file_script')
        self.upload_document(delete_file_script, self.doc_code, 'file_name.svg', b'xyzpdq')

        delete_file_script_files = self.get_files_for_workflow(delete_file_script)
        self.assertEqual(1, len(delete_file_script_files))
        self.assertFalse(delete_file_script_files[0].archived)

        workflow_api = self.get_workflow_api(delete_file_script)
        task = workflow_api.next_task
        # This time, setting `study_wide` to False only deletes files for current workflow
        form_data = {'doc_codes': self.doc_code, 'study_wide': False}
        self.complete_form(delete_file_script, task, form_data)

        # The file for the delete file script is archived
        delete_file_script_files = self.get_files_for_workflow(delete_file_script)
        self.assertEqual(1, len(delete_file_script_files))
        self.assertTrue(delete_file_script_files[0].archived)

        # The files for hello_world and simple_form are not archived
        hello_world_files = self.get_files_for_workflow(hello_world)
        self.assertEqual(1, len(hello_world_files))
        self.assertFalse(hello_world_files[0].archived)

        simple_form_files = self.get_files_for_workflow(simple_form)
        self.assertEqual(1, len(simple_form_files))
        self.assertFalse(simple_form_files[0].archived)

    def test_delete_file_current_study_only(self):
        hello_world, simple_form = self.setup_workflows()

        # separate study, this file should be unaffected
        study = self.create_study(title='Yet Another Test Study')
        workflow = self.create_workflow('empty_workflow', study=study)
        self.upload_document(workflow, self.doc_code, 'file_name.svg', b'xyzpdq')

        # nothing is archived
        workflow_files = self.get_files_for_workflow(workflow)
        self.assertFalse(workflow_files[0].archived)

        hello_world_files = self.get_files_for_workflow(hello_world)
        self.assertFalse(hello_world_files[0].archived)

        simple_form_files = self.get_files_for_workflow(simple_form)
        self.assertFalse(simple_form_files[0].archived)

        # delete files, should be limited to this study
        delete_file_script = self.create_workflow('delete_file_script')
        workflow_api = self.get_workflow_api(delete_file_script)
        task = workflow_api.next_task
        form_data = {'doc_codes': self.doc_code}
        self.complete_form(delete_file_script, task, form_data)

        # files from other study are unaffected
        workflow_files = self.get_files_for_workflow(workflow)
        self.assertFalse(workflow_files[0].archived)

        # files for this study are archived
        hello_world_files = self.get_files_for_workflow(hello_world)
        self.assertTrue(hello_world_files[0].archived)

        simple_form_files = self.get_files_for_workflow(simple_form)
        self.assertTrue(simple_form_files[0].archived)

        print('test_delete_file_current_study_only')

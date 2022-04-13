from github import UnknownObjectException

from tests.base_test import BaseTest
from unittest.mock import Mock

from crc.services.workflow_processor import WorkflowProcessor
from crc.services.user_file_service import UserFileService


class FakeGithubCreates(Mock):
    def get_user(var):
        class FakeUser(Mock):
            def get_repo(var, name):
                class FakeRepo(Mock):
                    def get_contents(var, filename, ref):
                        raise UnknownObjectException(status='Failure', data='Failed data', headers=[])
                    def update_file(var, path, message, content, sha, branch):
                        pass
                return FakeRepo()
        return FakeUser()


class FakeGithub(Mock):
    def get_user(var):
        class FakeUser(Mock):
            def get_repo(var, name):
                class FakeRepo(Mock):
                    def get_contents(var, filename, ref):
                        fake_file = Mock()
                        fake_file.decoded_content = b'Some bytes'
                        fake_file.path = '/el/path/'
                        fake_file.data = 'Serious data'
                        fake_file.sha = 'Sha'
                        return fake_file
                    def get_branches(var):
                        branch1 = Mock()
                        branch1.name = 'branch1'
                        branch2 = Mock()
                        branch2.name = 'branch2'
                        master = Mock()
                        master.name = 'master'
                        return [branch1, branch2, master]
                    def update_file(var, path, message, content, sha, branch):
                        pass
                return FakeRepo()
        return FakeUser()


class TestFileService(BaseTest):
    """Largely tested via the test_file_api, and time is tight, but adding new tests here."""

    def test_add_file_from_task_increments_version_and_replaces_on_subsequent_add(self):
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=task.get_name(),
                                          name="anything.png", content_type="text",
                                          binary_data=b'1234', irb_doc_code=irb_code)
        # Add the file again with different data
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=task.get_name(),
                                          name="anything.png", content_type="text",
                                          binary_data=b'5678', irb_doc_code=irb_code)

        file_models = UserFileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_models))

        file_data = UserFileService.get_workflow_data_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_data))
        self.assertEqual(2, file_data[0].version)
        self.assertEqual(4, file_data[0].size) # File dat size is included.

    def test_add_file_from_form_increments_version_and_replaces_on_subsequent_add_with_same_name(self):
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234')
        # Add the file again with different data
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678')

    def test_add_file_from_form_allows_multiple_files_with_different_names(self):
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234')
        # Add the file again with different data
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="a_different_thing.png", content_type="text",
                                      binary_data=b'5678')
        file_models = UserFileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(2, len(file_models))


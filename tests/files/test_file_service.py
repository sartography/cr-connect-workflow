from github import UnknownObjectException
from sqlalchemy import desc, column
from tests.base_test import BaseTest
from unittest.mock import patch, Mock

from crc import db, session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES
from crc.models.workflow import WorkflowModel, WorkflowSpecModel
from crc.services.file_service import FileService
from crc.services.spec_file_service import SpecFileService
from crc.services.workflow_processor import WorkflowProcessor


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
        self.load_example_data()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code)
        # Add the file again with different data
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code=irb_code)

        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_models))

        file_data = FileService.get_workflow_data_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_data))
        self.assertEqual(2, file_data[0].version)
        self.assertEqual(4, file_data[0].size) # File dat size is included.

    def test_add_file_from_form_increments_version_and_replaces_on_subsequent_add_with_same_name(self):
        self.load_example_data()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234')
        # Add the file again with different data
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678')

    def test_replace_archive_file_unarchives_the_file_and_updates(self):
        self.load_example_data()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234')

        # Archive the file
        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_models))
        file_model = file_models[0]
        file_model.archived = True
        db.session.add(file_model)

        # Assure that the file no longer comes back.
        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(0, len(file_models))

        # Add the file again with different data
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678')

        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_models))

        file_data = FileService.get_workflow_data_files(workflow_id=workflow.id)

        self.assertEqual(1, len(file_data))
        self.assertEqual(2, file_data[0].version)
        self.assertEqual(b'5678', file_data[0].data)

    def test_add_file_from_form_allows_multiple_files_with_different_names(self):
        self.load_example_data()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234')
        # Add the file again with different data
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      task_spec_name=task.get_name(),
                                      name="a_different_thing.png", content_type="text",
                                      binary_data=b'5678')
        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(2, len(file_models))

    @patch('crc.services.file_service.Github')
    def test_update_from_github(self, mock_github):
        mock_github.return_value = FakeGithub()

        self.load_example_data()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        file_model = FileService.add_workflow_file(workflow_id=workflow.id,
                                                   irb_doc_code=irb_code,
                                                   task_spec_name=task.get_name(),
                                                   name="anything.png", content_type="text",
                                                   binary_data=b'1234')
        FileService.update_from_github([file_model.id])

        file_model_data = FileDataModel.query.filter_by(
            file_model_id=file_model.id
        ).order_by(
            desc(FileDataModel.version)
        ).first()
        self.assertEqual(file_model_data.data, b'Some bytes')

    @patch('crc.services.file_service.Github')
    def test_publish_to_github_creates(self, mock_github):
        mock_github.return_value = FakeGithubCreates()

        self.load_example_data()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        file_model = FileService.add_workflow_file(workflow_id=workflow.id,
                                                   irb_doc_code=irb_code,
                                                   task_spec_name=task.get_name(),
                                                   name="anything.png", content_type="text",
                                                   binary_data=b'1234')
        result = FileService.publish_to_github([file_model.id])

        self.assertEqual(result['created'], True)

    @patch('crc.services.file_service.Github')
    def test_publish_to_github_updates(self, mock_github):
        mock_github.return_value = FakeGithub()

        self.load_example_data()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        file_model = FileService.add_workflow_file(workflow_id=workflow.id,
                                                   irb_doc_code=irb_code,
                                                   task_spec_name=task.get_name(),
                                                   name="anything.png", content_type="text",
                                                   binary_data=b'1234')
        result = FileService.publish_to_github([file_model.id])

        self.assertEqual(result['updated'], True)

    @patch('crc.services.file_service.Github')
    def test_get_repo_branches(self, mock_github):
        mock_github.return_value = FakeGithub()

        branches = FileService.get_repo_branches()

        self.assertIsInstance(branches, list)

    def test_add_workflow_spec_file(self):

        self.load_example_data()
        spec = db.session.query(WorkflowSpecModel).first()

        file_data = b"abcdef"
        file_name = 'random_fact.svg'
        content_type = CONTENT_TYPES[file_name[-3:]]

        # This creates a file on the filesystem
        file_model = SpecFileService().add_workflow_spec_file(spec, file_name, content_type, file_data)

        # This reads from a file on the filesystem
        spec_file_data = SpecFileService().get_spec_file_data(file_model.id).data

        self.assertEqual(file_data, spec_file_data)

    def test_delete_workflow_spec_file(self):
        self.load_example_data()
        file_model = session.query(FileModel).filter(column('workflow_spec_id').isnot(None)).first()
        file_data_before = SpecFileService().get_spec_file_data(file_model.id).data
        self.assertGreater(len(file_data_before), 0)

        SpecFileService().delete_spec_file(file_model.id)

        with self.assertRaises(ApiError) as ae:
            SpecFileService().get_spec_file_data(file_model.id)

        self.assertIn('No model found for file with file_id', ae.exception.message)
        print('test_delete_workflow_spec_file')

    def test_get_spec_files(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel.id).first()
        spec_files = SpecFileService().get_spec_files(spec.id)
        workflow = session.query(WorkflowModel).first()
        processor = WorkflowProcessor(workflow)
        self.assertIsInstance(processor, WorkflowProcessor)
        print('test_get_spec_files')

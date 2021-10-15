import base64

from github import UnknownObjectException
from sqlalchemy import desc

from crc.models.workflow import WorkflowSpecModel
from tests.base_test import BaseTest
from unittest.mock import patch, Mock

from crc import db
from crc.models.file import FileDataModel, FileModel
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor



class FakeInputGitTreeElement(Mock):
    def dummy(self,test):
        pass # meaningless local function

class FakeBlob(Mock):
    added_items = []
    def __init__(self,*args,**kwargs):
        super(FakeBlob,self).__init__(*args,**kwargs)
        self.sha = 'abc123'
        if len(args[0]) < 100:
            self.added_items.append(args[0])
    @classmethod
    def zaplist(cls):
        cls.added_items=[]

class FakeRepo(Mock):
    def create_git_tree(self,item):
        return FakeBlob('newtree')

    def get_contents(var, filename, ref):
        fake_file = Mock()
        fake_file.decoded_content = b'Some bytes'
        fake_file.path = '/el/path/'
        fake_file.data = 'Serious data'
        fake_file.sha = 'Sha'
        return fake_file

    def create_git_blob(var, data, type):
        return FakeBlob(data)

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




class FakeGithub(Mock):
    """ this mocks out the entire Github object.
        get_user().get_repo returns a repository object.

    """

    def get_user(self):
        print('yep made it')
        class FakeUser(Mock):
            def get_repo(self, name):
                return FakeRepo()
        return FakeUser()


class TestFileService(BaseTest):
    """Largely tested via the test_file_api, and time is tight, but adding new tests here."""

    def test_add_file_from_task_increments_version_and_replaces_on_subsequent_add(self):
        self.load_example_data()
        self.create_reference_document()
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
        self.create_reference_document()
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
        self.create_reference_document()
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
        self.create_reference_document()
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
    @patch('crc.services.file_service.InputGitTreeElement')

    def test_publish_to_github_creates(self, mock_element, mock_github):
        mock_github.return_value = FakeGithub()
        mock_element.return_value = FakeInputGitTreeElement()
        self.load_example_data()
        wf_spec = WorkflowSpecModel()
        wf_spec.id = 'abcdefg'
        wf_spec.display_name = 'New Workflow - Yum!!'
        wf_spec.name = 'my_new_workflow'
        wf_spec.description = 'yep - its a new workflow'
        wf_spec.category_id = 0
        wf_spec.display_order = 0
        db.session.add(wf_spec)
        db.session.commit()
        filedata = b'this is a test'
        FileService.add_workflow_spec_file(wf_spec, 'dummyfile.txt', 'text', filedata)
        filedata64 = base64.b64encode(filedata).decode('utf-8')
        result = FileService.publish_to_github('Test Github stuff')
        testblob = FakeBlob('nothing','nothing')
        filemodel = db.session.query(FileModel).filter(FileModel.workflow_spec_id==wf_spec.id).first()
        filedata = db.session.query(FileDataModel).filter(FileDataModel.file_model_id == filemodel.id).first()
        self.assertEqual('abc123',filedata.sha)
        self.assertIn(filedata64,testblob.added_items)
        self.assertEqual(result['updated'], True)

    @patch('crc.services.file_service.Github')
    @patch('crc.services.file_service.InputGitTreeElement')
    def test_publish_to_github_updates(self, mock_element,mock_github):
        mock_github.return_value = FakeGithub()
        mock_element.return_value = FakeInputGitTreeElement()
        self.load_example_data()

        # lets make sure we have a file with a small payload
        # essentially, we add a new workflow with a file, commit it
        # change the file and make sure it gets added in the second pass.

        wf_spec = WorkflowSpecModel()
        wf_spec.id = 'abcdefg'
        wf_spec.display_name = 'New Workflow - Yum!!'
        wf_spec.name = 'my_new_workflow'
        wf_spec.description = 'yep - its a new workflow'
        wf_spec.category_id = 0
        wf_spec.display_order = 0
        db.session.add(wf_spec)
        db.session.commit()
        filedata = b'this is a test'
        filedata64a = base64.b64encode(filedata).decode('utf-8')
        FileService.add_workflow_spec_file(wf_spec, 'dummyfile.txt', 'text', filedata)
        # publish so we have a baseline where everything is committed
        result = FileService.publish_to_github('Test Github stuff')
        # check to make sure all files have been committed
        needs_publish = FileService.need_github_update()
        self.assertEqual(needs_publish,False)
        firstfile = db.session.query(FileModel).filter(FileModel.workflow_spec_id==wf_spec.id).first()
        filedata = b'this is a secondtest'
        filedata64 = base64.b64encode(filedata).decode('utf-8')
        FileService.update_file(file_model=firstfile,binary_data=filedata,content_type='txt')
        needs_publish = FileService.need_github_update()
        self.assertEqual(needs_publish,True)
        # clear the list of commits
        FakeBlob.zaplist()
        result = FileService.publish_to_github('Test Github Update')
        testblob = FakeBlob('nothing', 'nothing')
        # make sure we committed the new file, but not the old file
        self.assertIn(filedata64, testblob.added_items)
        self.assertNotIn(filedata64a, testblob.added_items)
        self.assertEqual(result['updated'], True)


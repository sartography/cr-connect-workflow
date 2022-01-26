from tests.base_test import BaseTest
from crc import session
from crc.api.common import ApiError
from crc.models.workflow import WorkflowSpecModel
from crc.services.spec_file_service import SpecFileService


class TestDuplicateWorkflowSpecFile(BaseTest):

    def test_duplicate_workflow_spec_file(self):
        # We want this to fail.
        # Users should not be able to upload a file that already exists.

        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()

        # Add a file
        file_model = SpecFileService.add_workflow_spec_file(spec,
                                                        name="something.png",
                                                        content_type="text",
                                                        binary_data=b'1234')
        self.assertEqual(file_model.name, 'something.png')
        self.assertEqual(file_model.content_type, 'text')

        # Try to add it again
        try:
            SpecFileService.add_workflow_spec_file(spec,
                                               name="something.png",
                                               content_type="text",
                                               binary_data=b'5678')
        except ApiError as ae:
            self.assertEqual(ae.message, 'If you want to replace the file, use the update mechanism.')

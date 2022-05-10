from tests.base_test import BaseTest
from flask_bpmn.api.common import ApiError
from crc.services.spec_file_service import SpecFileService


class TestDuplicateWorkflowSpecFile(BaseTest):

    def test_duplicate_workflow_spec_file(self):
        # We want this to fail.
        # Users should not be able to upload a file that already exists.


        spec = self.load_test_spec('random_fact')

        # Add a file
        file_model = SpecFileService.add_file(spec, "something.png", b'1234')
        self.assertEqual(file_model.name, 'something.png')
        self.assertEqual(file_model.content_type, 'image/png')

        # Try to add it again
        try:
            file_model = SpecFileService.add_file(spec, "something.png", b'1234')
        except ApiError as ae:
            self.assertEqual(ae.message, 'If you want to replace the file, use the update mechanism.')

from tests.base_test import BaseTest
from crc.services.workflow_service import WorkflowService


class TestDataStoreValidation(BaseTest):

    def test_data_store_validation(self):
        spec_model = self.load_test_spec('data_store_validation')
        result = WorkflowService.test_spec(spec_model.id)

        print('test_data_store_validation')

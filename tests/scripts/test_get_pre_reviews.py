from tests.base_test import BaseTest

from crc import app
from crc.services.protocol_builder import ProtocolBuilderService

from unittest.mock import patch


class TestGetPreReview(BaseTest):

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_pre_review(self, mock_get):
        workflow = self.create_workflow('pre_reviews')
        study_id = workflow.study_id

        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('pre_review.json')
        pre_reviews = ProtocolBuilderService.get_pre_reviews(study_id)

        self.assertEqual(2, len(pre_reviews))
        for i in range(2):
            self.assertEqual(pre_reviews[i]['COMMENTS'], f'This is my comment {i}')
            self.assertEqual(pre_reviews[i]['STATUS'], 'Record')
            self.assertEqual(pre_reviews[i]['DETAIL'], 'Study returned to PI.')
            self.assertEqual(pre_reviews[i]['EVENT_TYPE'], 299)
            self.assertEqual(pre_reviews[i]['FNAME'], f'Firstname_{i}')
            self.assertEqual(pre_reviews[i]['LNAME'], f'Lastname_{i}')
            self.assertEqual(pre_reviews[i]['LOGIN'], f'login_{i}')
            self.assertEqual(pre_reviews[i]['PROT_EVENT_ID'], i + 1)
            self.assertEqual(pre_reviews[i]['REVIEW_TYPE'], 2)
            self.assertEqual(pre_reviews[i]['SS_STUDY_ID'], pre_reviews[i]['UVA_STUDY_TRACKING'])
            self.assertEqual(pre_reviews[i]['IRBREVIEWERADMIN'], f'abc-{i}')

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_pre_review_error(self, mock_get):
        workflow = self.create_workflow('pre_reviews')
        study_id = workflow.study_id

        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('pre_review_error.json')
        pre_reviews = ProtocolBuilderService.get_pre_reviews(study_id)

        self.assertEqual(pre_reviews['STATUS'], 'Error')
        self.assertEqual(pre_reviews['DETAIL'], 'No records found.')

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_pre_review_script(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('pre_review.json')

        workflow = self.create_workflow('get_pre_reviews')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        data = task.data
        self.assertIn('pre_reviews', data)
        pre_reviews = data['pre_reviews']

        self.assertEqual(2, len(pre_reviews))
        for i in range(2):
            self.assertEqual(pre_reviews[i]['COMMENTS'], f'This is my comment {i}')
            self.assertEqual(pre_reviews[i]['STATUS'], 'Record')
            self.assertEqual(pre_reviews[i]['DETAIL'], 'Study returned to PI.')
            self.assertEqual(pre_reviews[i]['EVENT_TYPE'], 299)
            self.assertEqual(pre_reviews[i]['FNAME'], f'Firstname_{i}')
            self.assertEqual(pre_reviews[i]['LNAME'], f'Lastname_{i}')
            self.assertEqual(pre_reviews[i]['LOGIN'], f'login_{i}')
            self.assertEqual(pre_reviews[i]['PROT_EVENT_ID'], i + 1)
            self.assertEqual(pre_reviews[i]['REVIEW_TYPE'], 2)
            self.assertEqual(pre_reviews[i]['SS_STUDY_ID'], pre_reviews[i]['UVA_STUDY_TRACKING'])
            self.assertEqual(pre_reviews[i]['IRBREVIEWERADMIN'], f'abc-{i}')

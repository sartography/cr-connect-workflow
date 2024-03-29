from tests.base_test import BaseTest
from crc import session
from crc.models.study import StudyModel, StudyStatus, StudySchema, ProgressStatus
import json
from unittest.mock import patch


class TestStudyActionsStatus(BaseTest):

    def update_study_status(self, study, study_schema):
        self.app.put('/v1.0/study/%i' % study.id,
                     content_type="application/json",
                     headers=self.logged_in_headers(),
                     data=json.dumps(study_schema))

        # The error happened when the dashboard reloaded,
        # in particular, when we got the studies for the user
        api_response = self.app.get('/v1.0/study', headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)

        study_result = session.query(StudyModel).filter(StudyModel.id == study.id).first()
        return study_result

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    def test_hold_study(self, mock_details):
        self.add_studies()
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)

        study = session.query(StudyModel).first()
        self.assertEqual(study.status, StudyStatus.in_progress)

        study_schema = StudySchema().dump(study)
        study_schema['status'] = 'hold'
        study_schema['comment'] = 'This is my hold comment'

        study_result = self.update_study_status(study, study_schema)
        self.assertEqual(StudyStatus.hold, study_result.status)

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    def test_abandon_study(self, mock_details):
        self.add_studies()
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)

        study = session.query(StudyModel).first()
        self.assertEqual(study.status, StudyStatus.in_progress)

        study_schema = StudySchema().dump(study)
        study_schema['status'] = 'abandoned'
        study_schema['comment'] = 'This is my abandon comment'

        study_result = self.update_study_status(study, study_schema)
        self.assertEqual(StudyStatus.abandoned, study_result.status)

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    def test_open_enrollment_study(self, mock_details):
        self.add_studies()
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)

        study = session.query(StudyModel).first()
        self.assertEqual(study.status, StudyStatus.in_progress)

        study_schema = StudySchema().dump(study)
        study_schema['status'] = 'open_for_enrollment'
        study_schema['comment'] = 'This is my open enrollment comment'
        study_schema['enrollment_date'] = '2021-01-04T05:00:00.000Z'

        study_result = self.update_study_status(study, study_schema)
        self.assertEqual(StudyStatus.open_for_enrollment, study_result.status)
        self.assertEqual(ProgressStatus.finance_in_progress, study_result.progress_status)

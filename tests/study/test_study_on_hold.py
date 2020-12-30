from tests.base_test import BaseTest
from crc import session
from crc.models.study import StudyModel, StudyStatus, StudySchema
import json


class TestHoldStudy(BaseTest):

    def test_hold_study(self):
        self.load_example_data()

        study = session.query(StudyModel).first()
        self.assertEqual(study.status, StudyStatus.in_progress)

        study_schema = StudySchema().dump(study)
        study_schema['status'] = 'hold'
        study_schema['comment'] = 'This is my comment'

        self.app.put('/v1.0/study/%i' % study.id,
                     content_type="application/json",
                     headers=self.logged_in_headers(),
                     data=json.dumps(study_schema))

        # The error happened when the dashboard reloaded,
        # in particular, when we got the studies for the user
        api_response = self.app.get('/v1.0/study', headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)

        study_result = session.query(StudyModel).filter(StudyModel.id == study.id).first()
        self.assertEqual(StudyStatus.hold, study_result.status)

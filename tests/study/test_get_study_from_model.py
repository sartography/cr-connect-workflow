from tests.base_test import BaseTest
from crc import session
from crc.models.study import StudyModel
import json


class TestGetStudyFromModel(BaseTest):

    def test_get_study_from_model(self):

        self.load_example_data()
        study = session.query(StudyModel).order_by(StudyModel.id.desc()).first()
        id = study.id + 1
        result = self.app.get('/v1.0/study/%i' % id,
                              headers=self.logged_in_headers())
        json_data = json.loads(result.get_data(as_text=True))
        self.assertIn('code', json_data)
        self.assertEqual('empty_study_model', json_data['code'])
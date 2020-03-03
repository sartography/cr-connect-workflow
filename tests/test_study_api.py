import json
from datetime import datetime, timezone
from unittest.mock import patch

from crc import session
from crc.models.study import StudyModel, StudyModelSchema
from crc.models.protocol_builder import ProtocolBuilderStatus
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus, \
    WorkflowApiSchema
from tests.base_test import BaseTest


class TestStudyApi(BaseTest):

    def test_study_basics(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        self.assertIsNotNone(study)

    def test_add_study(self):
        self.load_example_data()
        study = {
            "id": 12345,
            "title": "Phase III Trial of Genuine People Personalities (GPP) Autonomous Intelligent Emotional Agents "
                     "for Interstellar Spacecraft",
            "last_updated": datetime.now(tz=timezone.utc),
            "protocol_builder_status": ProtocolBuilderStatus.in_process,
            "primary_investigator_id": "tricia.marie.mcmillan@heartofgold.edu",
            "sponsor": "Sirius Cybernetics Corporation",
            "ind_number": "567890",
            "user_uid": "dhf8r",
        }
        rv = self.app.post('/v1.0/study',
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(StudyModelSchema().dump(study)))
        self.assert_success(rv)
        db_study = session.query(StudyModel).filter_by(id=12345).first()
        self.assertIsNotNone(db_study)
        self.assertEqual(study["title"], db_study.title)
        self.assertAlmostEqual(study["last_updated"], db_study.last_updated)
        self.assertEqual(study["protocol_builder_status"], db_study.protocol_builder_status)
        self.assertEqual(study["primary_investigator_id"], db_study.primary_investigator_id)
        self.assertEqual(study["sponsor"], db_study.sponsor)
        self.assertEqual(study["ind_number"], db_study.ind_number)
        self.assertEqual(study["user_uid"], db_study.user_uid)

    def test_update_study(self):
        self.load_example_data()
        study: StudyModel = session.query(StudyModel).first()
        study.title = "Pilot Study of Fjord Placement for Single Fraction Outcomes to Cortisol Susceptibility"
        study.protocol_builder_status = ProtocolBuilderStatus.complete
        rv = self.app.put('/v1.0/study/%i' % study.id,
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(StudyModelSchema().dump(study)))
        self.assert_success(rv)
        db_study = session.query(StudyModel).filter_by(id=study.id).first()
        self.assertIsNotNone(db_study)
        self.assertEqual(study.title, db_study.title)
        self.assertEqual(study.protocol_builder_status, db_study.protocol_builder_status)


    @patch('crc.services.protocol_builder.requests.get')
    def test_get_all_studies(self, mock_get):
        self.load_example_data()
        db_studies_before = session.query(StudyModel).all()
        num_db_studies_before = len(db_studies_before)

        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('user_studies.json')
        # pb_response = ProtocolBuilderService.get_studies(self.test_uid)
        # self.assertIsNotNone(pb_response)

        self.load_example_data()
        api_response = self.app.get('/v1.0/study',
                          follow_redirects=True,
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(api_response)

        db_studies_after = session.query(StudyModel).all()
        num_db_studies_after = len(db_studies_after)
        self.assertGreater(num_db_studies_after, num_db_studies_before)

        json_data = json.loads(api_response.get_data(as_text=True))
        api_studies = StudyModelSchema(many=True).load(json_data, session=session)

        num_inactive = 0
        num_active = 0

        for study in api_studies:
            if study.inactive:
                num_inactive += 1
            else:
                num_active += 1

        self.assertEqual(num_inactive, num_db_studies_before)
        self.assertEqual(num_active, num_db_studies_after - num_db_studies_before)

    def test_study_api_get_single_study(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        rv = self.app.get('/v1.0/study/%i' % study.id,
                          follow_redirects=True,
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        study2 = StudyModelSchema().load(json_data, session=session)
        self.assertEqual(study, study2)
        self.assertEqual(study.id, study2.id)
        self.assertEqual(study.title, study2.title)
        self.assertEqual(study.last_updated, study2.last_updated)
        self.assertEqual(study.protocol_builder_status, study2.protocol_builder_status)
        self.assertEqual(study.primary_investigator_id, study2.primary_investigator_id)
        self.assertEqual(study.sponsor, study2.sponsor)
        self.assertEqual(study.ind_number, study2.ind_number)

    def test_add_workflow_to_study(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        self.assertEqual(0, session.query(WorkflowModel).count())
        spec = session.query(WorkflowSpecModel).first()
        rv = self.app.post('/v1.0/study/%i/workflows' % study.id,
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(rv)
        self.assertEqual(1, session.query(WorkflowModel).count())
        workflow_model = session.query(WorkflowModel).first()
        self.assertEqual(study.id, workflow_model.study_id)
        self.assertEqual(WorkflowStatus.user_input_required, workflow_model.status)
        self.assertIsNotNone(workflow_model.bpmn_workflow_json)
        self.assertEqual(spec.id, workflow_model.workflow_spec_id)

        json_data = json.loads(rv.get_data(as_text=True))
        workflow2 = WorkflowApiSchema().load(json_data)
        self.assertEqual(workflow_model.id, workflow2.id)

    def test_delete_workflow(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        spec = session.query(WorkflowSpecModel).first()
        rv = self.app.post('/v1.0/study/%i/workflows' % study.id,
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assertEqual(1, session.query(WorkflowModel).count())
        json_data = json.loads(rv.get_data(as_text=True))
        workflow = WorkflowApiSchema().load(json_data)
        rv = self.app.delete('/v1.0/workflow/%i' % workflow.id)
        self.assert_success(rv)
        self.assertEqual(0, session.query(WorkflowModel).count())

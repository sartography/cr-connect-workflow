import json
from datetime import datetime, timezone
from unittest.mock import patch, Mock

from crc import session
from crc.models.api_models import WorkflowApiSchema, WorkflowApi
from crc.models.study import StudyModel, StudyModelSchema
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudyDetailsSchema, \
    ProtocolBuilderStudySchema
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus
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
            "protocol_builder_status": ProtocolBuilderStatus.IN_PROCESS,
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
        study.protocol_builder_status = ProtocolBuilderStatus.REVIEW_COMPLETE
        rv = self.app.put('/v1.0/study/%i' % study.id,
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(StudyModelSchema().dump(study)))
        self.assert_success(rv)
        db_study = session.query(StudyModel).filter_by(id=study.id).first()
        self.assertIsNotNone(db_study)
        self.assertEqual(study.title, db_study.title)
        self.assertEqual(study.protocol_builder_status, db_study.protocol_builder_status)

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')  # mock_studies
    def test_get_all_studies(self, mock_studies, mock_details):
        self.load_example_data()
        db_studies_before = session.query(StudyModel).all()
        num_db_studies_before = len(db_studies_before)

        # Mock Protocol Builder response
        studies_response = self.protocol_builder_response('user_studies.json')
        mock_studies.return_value = ProtocolBuilderStudySchema(many=True).loads(studies_response)

        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = ProtocolBuilderStudyDetailsSchema().loads(details_response)

        self.load_example_data()
        api_response = self.app.get('/v1.0/study',
                          follow_redirects=True,
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(api_response)
        json_data = json.loads(api_response.get_data(as_text=True))
        api_studies = StudyModelSchema(many=True).load(json_data, session=session)

        num_inactive = 0
        num_active = 0

        for study in api_studies:
            if study.inactive:
                num_inactive += 1
            else:
                num_active += 1

        db_studies_after = session.query(StudyModel).all()
        num_db_studies_after = len(db_studies_after)
        self.assertGreater(num_db_studies_after, num_db_studies_before)
        self.assertGreater(num_inactive, 0)
        self.assertGreater(num_active, 0)
        self.assertEqual(len(api_studies), num_db_studies_after)
        self.assertEqual(num_active + num_inactive, num_db_studies_after)

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

    def test_delete_study(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        rv = self.app.delete('/v1.0/study/%i' % study.id)
        self.assert_success(rv)

    def test_delete_study_with_workflow(self):
        self.load_example_data()
        study = session.query(StudyModel).first()

        spec = session.query(WorkflowSpecModel).first()
        rv = self.app.post('/v1.0/study/%i/workflows' % study.id,
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))

        rv = self.app.delete('/v1.0/study/%i' % study.id)
        self.assert_failure(rv, error_code="study_integrity_error")

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
        rv = self.app.delete('/v1.0/workflow/%i' % workflow.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertEqual(0, session.query(WorkflowModel).count())

    def test_get_study_workflows(self):
        self.load_example_data()

        # Should have no workflows to start
        study = session.query(StudyModel).first()
        response_before = self.app.get('/v1.0/study/%i/workflows' % study.id,
                           content_type="application/json",
                           headers=self.logged_in_headers())
        self.assert_success(response_before)
        json_data_before = json.loads(response_before.get_data(as_text=True))
        workflows_before = WorkflowApiSchema(many=True).load(json_data_before)
        self.assertEqual(0, len(workflows_before))

        # Add a workflow
        spec = session.query(WorkflowSpecModel).first()
        add_response = self.app.post('/v1.0/study/%i/workflows' % study.id,
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(add_response)

        # Should have one workflow now
        response_after = self.app.get('/v1.0/study/%i/workflows' % study.id,
                           content_type="application/json",
                           headers=self.logged_in_headers())
        self.assert_success(response_after)
        json_data_after = json.loads(response_after.get_data(as_text=True))
        workflows_after = WorkflowApiSchema(many=True).load(json_data_after)
        self.assertEqual(1, len(workflows_after))

    """
    Workflow Specs that have been made available (or not) to a particular study via the status.bpmn should be flagged
    as available (or not) when the list of a study's workflows is retrieved.
    """
    def test_workflow_spec_status(self):
        self.load_example_data()
        study = session.query(StudyModel).first()

        # Add status workflow
        self.load_test_spec('status')

        # Add status workflow to the study
        status_spec = session.query(WorkflowSpecModel).filter_by(is_status=True).first()
        add_status_response = self.app.post('/v1.0/study/%i/workflows' % study.id,
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(WorkflowSpecModelSchema().dump(status_spec)))
        self.assert_success(add_status_response)
        json_data_status = json.loads(add_status_response.get_data(as_text=True))
        status_workflow: WorkflowApi = WorkflowApiSchema().load(json_data_status)
        status_task_id = status_workflow.next_task['id']

        # Add all available non-status workflows to the study
        specs = session.query(WorkflowSpecModel).filter_by(is_status=False).all()
        for spec in specs:
            add_response = self.app.post('/v1.0/study/%i/workflows' % study.id,
                               content_type="application/json",
                               headers=self.logged_in_headers(),
                               data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
            self.assert_success(add_response)

        for is_active in [False, True]:
            # Update status task data
            update_status_response = self.app.put('/v1.0/workflow/%i/task/%s/data' % (status_workflow.id, status_task_id),
                              headers=self.logged_in_headers(),
                              content_type="application/json",
                              data=json.dumps({'some_input': is_active}))
            self.assert_success(update_status_response)

            # List workflows for study
            response_after = self.app.get('/v1.0/study/%i/workflows' % study.id,
                               content_type="application/json",
                               headers=self.logged_in_headers())
            self.assert_success(response_after)

            json_data_after = json.loads(response_after.get_data(as_text=True))
            workflows_after = WorkflowApiSchema(many=True).load(json_data_after)
            self.assertEqual(len(specs), len(workflows_after))

            for workflow in workflows_after:
                self.assertEqual(workflow.is_active, is_active)


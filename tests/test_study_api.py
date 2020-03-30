import json
from datetime import datetime, timezone
from unittest.mock import patch

from crc import session
from crc.models.api_models import WorkflowApiSchema
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudyDetailsSchema, \
    ProtocolBuilderStudySchema
from crc.models.study import StudyModel, StudySchema
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus, \
    WorkflowSpecCategoryModel
from tests.base_test import BaseTest


class TestStudyApi(BaseTest):

    TEST_STUDY = {
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

    def add_test_study(self):
        rv = self.app.post('/v1.0/study',
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(StudySchema().dump(self.TEST_STUDY)))
        self.assert_success(rv)
        return json.loads(rv.get_data(as_text=True))

    def test_study_basics(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        self.assertIsNotNone(study)

    def test_get_study(self):
        """Generic test, but pretty detailed, in that the study should return a categorized list of workflows
        This starts with out loading the example data, to show that all the bases are covered from ground 0."""
        new_study = self.add_test_study()
        new_study = session.query(StudyModel).filter_by(id=new_study["id"]).first()
        # Add a category
        new_category = WorkflowSpecCategoryModel(id=21, name="test_cat", display_name="Test Category", display_order=0)
        session.add(new_category)
        session.commit()
        # Create a workflow specification
        self.create_workflow("random_fact", study=new_study, category_id=new_category.id)
        # Assure there is a master specification, and it has the lookup files it needs.
        spec = self.load_test_spec("top_level_workflow", master_spec=True)
        self.create_reference_document()

        api_response = self.app.get('/v1.0/study/%i' % new_study.id,
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        study = StudySchema().loads(api_response.get_data(as_text=True))

        self.assertEqual(study.title, self.TEST_STUDY['title'])
        self.assertEqual(study.primary_investigator_id, self.TEST_STUDY['primary_investigator_id'])
        self.assertEqual(study.sponsor, self.TEST_STUDY['sponsor'])
        self.assertEqual(study.ind_number, self.TEST_STUDY['ind_number'])
        self.assertEqual(study.user_uid, self.TEST_STUDY['user_uid'])

        # Categories are read only, so switching to sub-scripting here.
        category = [c for c in study.categories if c['name'] == "test_cat"][0]
        self.assertEqual("test_cat", category['name'])
        self.assertEqual("Test Category", category['display_name'])
        self.assertEqual(1, len(category["workflows"]))
        workflow = category["workflows"][0]
        self.assertEqual("random_fact", workflow["name"])
        self.assertEqual("optional", workflow["state"])
        self.assertEqual("not_started", workflow["status"])
        self.assertEqual(0, workflow["total_tasks"])
        self.assertEqual(0, workflow["completed_tasks"])

    def test_add_study(self):
        self.load_example_data()
        study = self.add_test_study()
        db_study = session.query(StudyModel).filter_by(id=12345).first()
        self.assertIsNotNone(db_study)
        self.assertEqual(study["title"], db_study.title)
        self.assertEqual(study["primary_investigator_id"], db_study.primary_investigator_id)
        self.assertEqual(study["sponsor"], db_study.sponsor)
        self.assertEqual(study["ind_number"], db_study.ind_number)
        self.assertEqual(study["user_uid"], db_study.user_uid)

        workflow_spec_count =session.query(WorkflowSpecModel).filter(WorkflowSpecModel.is_master_spec == False).count()
        workflow_count = session.query(WorkflowModel).filter(WorkflowModel.study_id == 12345).count()
        error_count = len(study["errors"])
        self.assertEquals(workflow_spec_count, workflow_count + error_count)

    def test_update_study(self):
        self.load_example_data()
        study: StudyModel = session.query(StudyModel).first()
        study.title = "Pilot Study of Fjord Placement for Single Fraction Outcomes to Cortisol Susceptibility"
        study.protocol_builder_status = ProtocolBuilderStatus.REVIEW_COMPLETE
        rv = self.app.put('/v1.0/study/%i' % study.id,
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(StudySchema().dump(study)))
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(study.title, json_data['title'])
        self.assertEqual(study.protocol_builder_status.name, json_data['protocol_builder_status'])

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')  # mock_studies
    def test_get_all_studies(self, mock_studies, mock_details):
        self.load_example_data()
        s = StudyModel(
            id=54321,  # This matches one of the ids from the study_details_json data.
            title='The impact of pandemics on dog owner sanity after 12 days',
            user_uid='dhf8r',
        )
        session.add(s)
        session.commit()

        num_db_studies_before = session.query(StudyModel).count()

        # Mock Protocol Builder responses
        studies_response = self.protocol_builder_response('user_studies.json')
        mock_studies.return_value = ProtocolBuilderStudySchema(many=True).loads(studies_response)
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = ProtocolBuilderStudyDetailsSchema().loads(details_response)

        # Make the api call to get all studies
        api_response = self.app.get('/v1.0/study', headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        json_data = json.loads(api_response.get_data(as_text=True))

        num_inactive = 0
        num_active = 0

        for study in json_data:
            if study['inactive']:
                num_inactive += 1
            else:
                num_active += 1

        db_studies_after = session.query(StudyModel).all()
        num_db_studies_after = len(db_studies_after)
        self.assertGreater(num_db_studies_after, num_db_studies_before)
        self.assertGreater(num_inactive, 0)
        self.assertGreater(num_active, 0)
        self.assertEqual(len(json_data), num_db_studies_after)
        self.assertEqual(num_active + num_inactive, num_db_studies_after)

        # Assure that the existing study is properly updated.
        test_study = session.query(StudyModel).filter_by(id=54321).first()
        self.assertFalse(test_study.inactive)

    def test_get_single_study(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        rv = self.app.get('/v1.0/study/%i' % study.id,
                          follow_redirects=True,
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(study.id, json_data['id'])
        self.assertEqual(study.title, json_data['title'])
        self.assertEqual(study.protocol_builder_status.name, json_data['protocol_builder_status'])
        self.assertEqual(study.primary_investigator_id, json_data['primary_investigator_id'])
        self.assertEqual(study.sponsor, json_data['sponsor'])
        self.assertEqual(study.ind_number, json_data['ind_number'])

    def test_delete_study(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        rv = self.app.delete('/v1.0/study/%i' % study.id, headers=self.logged_in_headers())
        self.assert_success(rv)

    # """
    # Workflow Specs that have been made available (or not) to a particular study via the status.bpmn should be flagged
    # as available (or not) when the list of a study's workflows is retrieved.
    # """
    # @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')
    # @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')
    # @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')
    # @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')
    # def test_workflow_spec_status(self,
    #                               mock_details,
    #                               mock_required_docs,
    #                               mock_investigators,
    #                               mock_studies):
    #
    #     # Mock Protocol Builder response
    #     studies_response = self.protocol_builder_response('user_studies.json')
    #     mock_studies.return_value = ProtocolBuilderStudySchema(many=True).loads(studies_response)
    #
    #     investigators_response = self.protocol_builder_response('investigators.json')
    #     mock_investigators.return_value = ProtocolBuilderInvestigatorSchema(many=True).loads(investigators_response)
    #
    #     required_docs_response = self.protocol_builder_response('required_docs.json')
    #     mock_required_docs.return_value = ProtocolBuilderRequiredDocumentSchema(many=True).loads(required_docs_response)
    #
    #     details_response = self.protocol_builder_response('study_details.json')
    #     mock_details.return_value = ProtocolBuilderStudyDetailsSchema().loads(details_response)
    #
    #     self.load_example_data()
    #     study = session.query(StudyModel).first()
    #     study_id = study.id
    #
    #     # Add status workflow
    #     self.load_test_spec('top_level_workflow')
    #
    #     # Assure the top_level_workflow is added to the study
    #     top_level_spec = session.query(WorkflowSpecModel).filter_by(is_master_spec=True).first()
    #     self.assertIsNotNone(top_level_spec)
    #
    #
    #
    #     for is_active in [False, True]:
    #         # Set all workflow specs to inactive|active
    #         update_status_response = self.app.put('/v1.0/workflow/%i/task/%s/data' % (status_workflow.id, status_task_id),
    #                           headers=self.logged_in_headers(),
    #                           content_type="application/json",
    #                           data=json.dumps({'some_input': is_active}))
    #         self.assert_success(update_status_response)
    #         json_workflow_api = json.loads(update_status_response.get_data(as_text=True))
    #         updated_workflow_api: WorkflowApi = WorkflowApiSchema().load(json_workflow_api)
    #         self.assertIsNotNone(updated_workflow_api)
    #         self.assertEqual(updated_workflow_api.status, WorkflowStatus.complete)
    #         self.assertIsNotNone(updated_workflow_api.last_task)
    #         self.assertIsNotNone(updated_workflow_api.last_task['data'])
    #         self.assertIsNotNone(updated_workflow_api.last_task['data']['some_input'])
    #         self.assertEqual(updated_workflow_api.last_task['data']['some_input'], is_active)
    #
    #         # List workflows for study
    #         response_after = self.app.get('/v1.0/study/%i/workflows' % study.id,
    #                            content_type="application/json",
    #                            headers=self.logged_in_headers())
    #         self.assert_success(response_after)
    #
    #         json_data_after = json.loads(response_after.get_data(as_text=True))
    #         workflows_after = WorkflowApiSchema(many=True).load(json_data_after)
    #         self.assertEqual(len(specs), len(workflows_after))
    #
    #         # All workflows should be inactive|active
    #         for workflow in workflows_after:
    #             self.assertEqual(workflow.is_active, is_active)


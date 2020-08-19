import json
from profile import Profile

from tests.base_test import BaseTest

from datetime import datetime, timezone
from unittest.mock import patch

from crc import session, app
from crc.models.protocol_builder import ProtocolBuilderStatus, \
    ProtocolBuilderStudySchema
from crc.models.approval import ApprovalStatus
from crc.models.file import FileModel
from crc.models.task_event import TaskEventModel
from crc.models.study import StudyEvent, StudyModel, StudySchema, StudyStatus, StudyEventType
from crc.models.workflow import WorkflowSpecModel, WorkflowModel
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService


class TestStudyApi(BaseTest):

    TEST_STUDY = {
        "title": "Phase III Trial of Genuine People Personalities (GPP) Autonomous Intelligent Emotional Agents "
                 "for Interstellar Spacecraft",
        "last_updated": datetime.now(tz=timezone.utc),
        "primary_investigator_id": "tmm2x",
        "user_uid": "dhf8r",
    }

    def add_test_study(self):
        study_schema = StudySchema().dump(self.TEST_STUDY)
        study_schema['status'] = StudyStatus.in_progress.value
        rv = self.app.post('/v1.0/study',
                           content_type="application/json",
                           headers=self.logged_in_headers(),
                           data=json.dumps(study_schema))
        self.assert_success(rv)
        return json.loads(rv.get_data(as_text=True))

    def test_study_basics(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        self.assertIsNotNone(study)

    def test_get_study(self):
        """Generic test, but pretty detailed, in that the study should return a categorized list of workflows
        This starts with out loading the example data, to show that all the bases are covered from ground 0."""

        """NOTE:  The protocol builder is not enabled or mocked out.  As the master workflow (which is empty),
        and the test workflow do not need it, and it is disabled in the configuration."""
        self.load_example_data()
        new_study = self.add_test_study()
        new_study = session.query(StudyModel).filter_by(id=new_study["id"]).first()

        api_response = self.app.get('/v1.0/study/%i' % new_study.id,
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        study = StudySchema().loads(api_response.get_data(as_text=True))

        self.assertEqual(study.title, self.TEST_STUDY['title'])
        self.assertEqual(study.primary_investigator_id, self.TEST_STUDY['primary_investigator_id'])
        self.assertEqual(study.user_uid, self.TEST_STUDY['user_uid'])

        # Categories are read only, so switching to sub-scripting here.
        # This assumes there is one test category set up in the example data.
        category = study.categories[0]
        self.assertEqual("test_category", category['name'])
        self.assertEqual("Test Category", category['display_name'])
        self.assertEqual(1, len(category["workflows"]))
        workflow = category["workflows"][0]
        self.assertEqual("random_fact", workflow["name"])
        self.assertEqual("optional", workflow["state"])
        self.assertEqual("not_started", workflow["status"])
        self.assertEqual(0, workflow["total_tasks"])
        self.assertEqual(0, workflow["completed_tasks"])

    def test_get_study_has_details_about_files(self):

        # Set up the study and attach a file to it.
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="png",
                                      binary_data=b'1234', irb_doc_code=irb_code)

        api_response = self.app.get('/v1.0/study/%i' % workflow.study_id,
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        study = StudySchema().loads(api_response.get_data(as_text=True))
        self.assertEqual(1, len(study.files))
        self.assertEqual("UVA Compliance/PRC Approval", study.files[0]["category"])
        self.assertEqual("Cancer Center's PRC Approval Form", study.files[0]["description"])
        self.assertEqual("UVA Compliance/PRC Approval.png", study.files[0]["download_name"])

        # TODO: WRITE A TEST FOR STUDY FILES

    def test_get_study_has_details_about_approvals(self):
        self.load_example_data()
        full_study = self._create_study_workflow_approvals(
            user_uid="dhf8r", title="first study", primary_investigator_id="lb3dp",
            approver_uids=["lb3dp", "dhf8r"], statuses=[ApprovalStatus.PENDING.value, ApprovalStatus.PENDING.value]
        )

        api_response = self.app.get('/v1.0/study/%i' % full_study['study'].id,
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        study = StudySchema().loads(api_response.get_data(as_text=True))

        self.assertEqual(len(study.approvals), 2)

        for approval in study.approvals:
            self.assertEqual(full_study['study'].title, approval['title'])

    def test_add_study(self):
        self.load_example_data()
        study = self.add_test_study()
        db_study = session.query(StudyModel).filter_by(id=study['id']).first()
        self.assertIsNotNone(db_study)
        self.assertEqual(study["title"], db_study.title)
        self.assertEqual(study["primary_investigator_id"], db_study.primary_investigator_id)
        self.assertEqual(study["sponsor"], db_study.sponsor)
        self.assertEqual(study["ind_number"], db_study.ind_number)
        self.assertEqual(study["user_uid"], db_study.user_uid)

        workflow_spec_count =session.query(WorkflowSpecModel).filter(WorkflowSpecModel.is_master_spec == False).count()
        workflow_count = session.query(WorkflowModel).filter(WorkflowModel.study_id == study['id']).count()
        error_count = len(study["errors"])
        self.assertEqual(workflow_spec_count, workflow_count + error_count)

        study_event = session.query(StudyEvent).first()
        self.assertIsNotNone(study_event)
        self.assertEqual(study_event.status, StudyStatus.in_progress)
        self.assertEqual(study_event.event_type, StudyEventType.user)
        self.assertFalse(study_event.comment)
        self.assertEqual(study_event.user_uid, self.test_uid)

    def test_update_study(self):
        self.load_example_data()
        update_comment = 'Updating the study'
        study: StudyModel = session.query(StudyModel).first()
        study.title = "Pilot Study of Fjord Placement for Single Fraction Outcomes to Cortisol Susceptibility"
        study_schema = StudySchema().dump(study)
        study_schema['status'] = StudyStatus.hold.value
        study_schema['comment'] = update_comment
        rv = self.app.put('/v1.0/study/%i' % study.id,
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(study_schema))
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(study.title, json_data['title'])
        self.assertEqual(study.status.value, json_data['status'])

        # Making sure events history is being properly recorded
        study_event = session.query(StudyEvent).first()
        self.assertIsNotNone(study_event)
        self.assertEqual(study_event.status, StudyStatus.hold)
        self.assertEqual(study_event.event_type, StudyEventType.user)
        self.assertEqual(study_event.comment, update_comment)
        self.assertEqual(study_event.user_uid, self.test_uid)

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')  # mock_studies
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')  # mock_studies
    def test_get_all_studies(self, mock_studies, mock_details, mock_docs, mock_investigators):
        # Enable the protocol builder for these tests, as the master_workflow and other workflows
        # depend on using the PB for data.
        app.config['PB_ENABLED'] = True
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
        mock_details.return_value = json.loads(details_response)
        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)
        investigators_response = self.protocol_builder_response('investigators.json')
        mock_investigators.return_value = json.loads(investigators_response)

        # Make the api call to get all studies
        api_response = self.app.get('/v1.0/study', headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        json_data = json.loads(api_response.get_data(as_text=True))

        num_abandoned = 0
        num_in_progress = 0
        num_open = 0

        for study in json_data:
            if study['status'] == 'abandoned': # One study does not exist in user_studies.json
                num_abandoned += 1
            if study['status'] == 'in_progress': # One study is marked complete without HSR Number
                num_in_progress += 1
            if study['status'] == 'open_for_enrollment':  # One study is marked complete and has an HSR Number
                num_open += 1

        db_studies_after = session.query(StudyModel).all()
        num_db_studies_after = len(db_studies_after)
        self.assertGreater(num_db_studies_after, num_db_studies_before)
        self.assertEqual(num_abandoned, 1)
        self.assertEqual(num_open, 1)
        self.assertEqual(num_in_progress, 2)
        self.assertEqual(len(json_data), num_db_studies_after)
        self.assertEqual(num_open + num_in_progress + num_abandoned, num_db_studies_after)

        # Automatic events check
        in_progress_events = session.query(StudyEvent).filter_by(status=StudyStatus.in_progress)
        self.assertEqual(in_progress_events.count(), 1)  # 1 study is in progress

        abandoned_events = session.query(StudyEvent).filter_by(status=StudyStatus.abandoned)
        self.assertEqual(abandoned_events.count(), 1)  # 1 study has been abandoned

        open_for_enrollment_events = session.query(StudyEvent).filter_by(status=StudyStatus.open_for_enrollment)
        self.assertEqual(open_for_enrollment_events.count(), 1)  # 1 study was moved to open for enrollment

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')  # mock_studies
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')  # mock_studies
    def test_get_single_study(self, mock_studies, mock_details, mock_docs, mock_investigators):

        # Mock Protocol Builder responses
        studies_response = self.protocol_builder_response('user_studies.json')
        mock_studies.return_value = ProtocolBuilderStudySchema(many=True).loads(studies_response)
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)
        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)
        investigators_response = self.protocol_builder_response('investigators.json')
        mock_investigators.return_value = json.loads(investigators_response)

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
        self.assertEqual(study.status.value, json_data['status'])
        self.assertEqual(study.primary_investigator_id, json_data['primary_investigator_id'])
        self.assertEqual(study.sponsor, json_data['sponsor'])
        self.assertEqual(study.ind_number, json_data['ind_number'])

    def test_delete_study(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        rv = self.app.delete('/v1.0/study/%i' % study.id, headers=self.logged_in_headers())
        self.assert_success(rv)

    def test_delete_workflow(self):
        self.load_example_data()
        workflow = session.query(WorkflowModel).first()
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code="UVACompl_PRCAppr" )

        workflow_files = session.query(FileModel).filter_by(workflow_id=workflow.id)
        self.assertEqual(workflow_files.count(), 1)
        workflow_files_ids = [file.id for file in workflow_files]

        rv = self.app.delete(f'/v1.0/workflow/{workflow.id}', headers=self.logged_in_headers())
        self.assert_success(rv)

        # No files should have the deleted workflow id anymore
        workflow_files = session.query(FileModel).filter_by(workflow_id=workflow.id)
        self.assertEqual(workflow_files.count(), 0)

        # Finally, let's confirm the file was archived
        workflow_files = session.query(FileModel).filter(FileModel.id.in_(workflow_files_ids))
        for file in workflow_files:
            self.assertTrue(file.archived)
            self.assertIsNone(file.workflow_id)

    def test_delete_study_with_workflow_and_status(self):
        self.load_example_data()
        workflow = session.query(WorkflowModel).first()
        stats1 = StudyEvent(
            study_id=workflow.study_id,
            status=StudyStatus.in_progress,
            comment='Some study status change event',
            event_type=StudyEventType.user,
            user_uid=self.users[0]['uid'],
        )
        stats2 = TaskEventModel(study_id=workflow.study_id, workflow_id=workflow.id, user_uid=self.users[0]['uid'])
        session.add_all([stats1, stats2])
        session.commit()
        rv = self.app.delete('/v1.0/study/%i' % workflow.study_id, headers=self.logged_in_headers())
        self.assert_success(rv)
        del_study = session.query(StudyModel).filter(StudyModel.id == workflow.study_id).first()
        self.assertIsNone(del_study)



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


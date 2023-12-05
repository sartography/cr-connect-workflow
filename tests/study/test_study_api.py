import json

from tests.base_test import BaseTest

from crc.services.ldap_service import LdapService

from datetime import datetime
from unittest.mock import patch

from crc.models.email import EmailModel, EmailDocCodesModel
from crc import session, app
from crc.models.protocol_builder import ProtocolBuilderCreatorStudySchema
from crc.models.file import FileModel
from crc.models.task_event import TaskEventModel
from crc.models.study import StudyEvent, StudyModel, StudySchema, StudyStatus, StudyEventType, StudyAssociated
from crc.models.workflow import WorkflowModel
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.user_file_service import UserFileService


class TestStudyApi(BaseTest):

    TEST_STUDY = {
        "title": "Phase III Trial of Genuine People Personalities (GPP) Autonomous Intelligent Emotional Agents "
                 "for Interstellar Spacecraft",
        "last_updated": datetime.utcnow(),
        "user_uid": "dhf8r",
        "review_type": 2
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
        self.add_studies()
        study = session.query(StudyModel).first()
        self.assertIsNotNone(study)

    def test_get_study(self):
        """Generic test, but pretty detailed, in that the study should return a categorized list of workflows
        This starts without loading the example data, to show that all the bases are covered from ground 0."""

        """NOTE:  The protocol builder is not enabled or mocked out.  As the master workflow (which is empty),
        and the test workflow do not need it, and it is disabled in the configuration."""
        self.load_test_spec('empty_workflow', master_spec=True)
        self.load_test_spec('random_fact')
        new_study = self.add_test_study()
        new_study = session.query(StudyModel).filter_by(id=new_study["id"]).first()

        api_response = self.app.get('/v1.0/study/%i?update_status=True' % new_study.id,
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        self.create_workflow('random_fact', study=new_study)

        study = StudySchema().loads(api_response.get_data(as_text=True))
        self.assertEqual(study.title, self.TEST_STUDY['title'])
        self.assertEqual(study.user_uid, self.TEST_STUDY['user_uid'])

        # Categories are read only, so switching to sub-scripting here.
        # This assumes there is one test category set up in the example data.
        category = study.categories[0]
        self.assertEqual("Test Workflows", category['display_name'])
        self.assertEqual(1, len(category["workflows"]))
        workflow = category["workflows"][0]
        self.assertEqual("random_fact", workflow["display_name"])
        self.assertEqual("optional", workflow["state"])
        self.assertEqual("not_started", workflow["status"])

    def test_get_study_updates_workflow_state(self):
        self.load_test_spec('test_master_workflow', master_spec=True)
        self.load_test_spec('simple_workflow')
        self.load_test_spec('empty_workflow')

        study = self.add_test_study()
        study_model = session.query(StudyModel).filter_by(id=study["id"]).first()

        # We should not have a state yet
        workflows = session.query(WorkflowModel).all()
        self.assertEqual('simple_workflow', workflows[0].workflow_spec_id)
        self.assertEqual('empty_workflow', workflows[1].workflow_spec_id)
        self.assertEqual(None, workflows[0].state)
        self.assertEqual(None, workflows[1].state)

        self.run_master_spec(study_model)

        workflows = session.query(WorkflowModel).all()
        self.assertEqual('simple_workflow', workflows[0].workflow_spec_id)
        self.assertEqual('empty_workflow', workflows[1].workflow_spec_id)
        self.assertEqual('required', workflows[0].state)
        self.assertEqual('locked', workflows[1].state)
        self.assertEqual('Completion of this workflow is required.', workflows[0].state_message)
        self.assertEqual('This workflow is locked', workflows[1].state_message)

    def test_get_study_has_details_about_files(self):
        self.load_test_spec('empty_workflow', master_spec=True)

        # Set up the study and attach a file to it.
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=task.get_name(),
                                          name="anything.png", content_type="png",
                                          binary_data=b'1234', irb_doc_code=irb_code)

        api_response = self.app.get('/v1.0/study/%i?update_status=True' % workflow.study_id,
                                    headers=self.logged_in_headers(), content_type="application/json")
        self.assert_success(api_response)
        study = StudySchema().loads(api_response.get_data(as_text=True))
        self.assertEqual(1, len(study.files))
        self.assertEqual("UVA Compliance", study.files[0]["document"]["category1"])
        self.assertEqual("Cancer Center's PRC Approval Form", study.files[0]["document"]["description"])

        # TODO: WRITE A TEST FOR STUDY FILES

    def test_add_study(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        study = self.add_test_study()
        db_study = session.query(StudyModel).filter_by(id=study['id']).first()
        self.assertIsNotNone(db_study)
        self.assertEqual(study["title"], db_study.title)
        self.assertEqual(study["sponsor"], db_study.sponsor)
        self.assertEqual(study["ind_number"], db_study.ind_number)
        self.assertEqual(study["user_uid"], db_study.user_uid)

        workflow_spec_count = len(self.workflow_spec_service.get_specs())
        workflow_count = session.query(WorkflowModel).filter(WorkflowModel.study_id == study['id']).count()
        self.assertEqual(workflow_spec_count, workflow_count)

        study_event = session.query(StudyEvent).first()
        self.assertIsNotNone(study_event)
        self.assertEqual(study_event.status, StudyStatus.in_progress)
        self.assertEqual(study_event.event_type, StudyEventType.user)
        self.assertFalse(study_event.comment)
        self.assertEqual(study_event.user_uid, self.test_uid)

    def test_update_study(self):
        self.add_studies()
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

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')  # mock_investigators
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')  # mock_studies
    def test_get_all_studies(self, mock_studies, mock_details, mock_docs, mock_investigators):
        # Enable the protocol builder for these tests, as the master_workflow and other workflows
        # depend on using the PB for data.
        app.config['PB_ENABLED'] = True
        app.config['PB_MIN_DATE'] = "2020-01-01T00:00:00.000Z"
        self.add_studies()
        with session.no_autoflush:
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
            mock_studies.return_value = ProtocolBuilderCreatorStudySchema(many=True).loads(studies_response)
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
                if study['status'] == 'open_for_enrollment':  # Currently, we don't automatically set studies to open for enrollment
                    num_open += 1
                if study['id'] == 65432:
                    # This study has `null` for DATELASTMODIFIED, so we should use the value in DATECREATED
                    self.assertEqual('2020-02-19T14:24:55.101695-05:00', study['last_updated'])
                if study['id'] == 11111:
                    self.assertTrue(False,"Study 11111 is too old to be processed and imported, it should be ignored.")
            db_studies_after = session.query(StudyModel).all()
            num_db_studies_after = len(db_studies_after)
            self.assertGreater(num_db_studies_after, num_db_studies_before)
            self.assertEqual(num_abandoned, 1)
            self.assertEqual(num_open, 0)  # Currently, we don't automatically set studies to open for enrollment
            self.assertEqual(num_in_progress, 2)
            self.assertEqual(len(json_data), num_db_studies_after)
            # The sum below is off, since we don't automatically set studies to Open for Enrollment
            # Leaving the test here because we will need it again
            # when we implement a new way to set Open for Enrollment
            # self.assertEqual(num_open + num_in_progress + num_abandoned, num_db_studies_after)

            # Automatic events check
            in_progress_events = session.query(StudyEvent).filter_by(status=StudyStatus.in_progress)
            self.assertEqual(in_progress_events.count(), 1)  # 1 study is in progress

            abandoned_events = session.query(StudyEvent).filter_by(status=StudyStatus.abandoned)
            self.assertEqual(abandoned_events.count(), 1)  # 1 study has been abandoned


            # We don't currently set any studies to Open for Enrollment automatically
            # Leaving the test here because we will need it again
            # when we implement a new way to set Open for Enrollment
            # open_for_enrollment_events = session.query(StudyEvent).filter_by(status=StudyStatus.open_for_enrollment)
            # self.assertEqual(open_for_enrollment_events.count(), 1)  # 1 study was moved to open for enrollment

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')  # mock_studies
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')  # mock_studies
    def test_get_single_study(self, mock_studies, mock_details, mock_docs, mock_investigators):

        # Mock Protocol Builder responses
        studies_response = self.protocol_builder_response('user_studies.json')
        mock_studies.return_value = ProtocolBuilderCreatorStudySchema(many=True).loads(studies_response)
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)
        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)
        investigators_response = self.protocol_builder_response('investigators.json')
        mock_investigators.return_value = json.loads(investigators_response)

        self.add_studies()
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
        self.assertEqual(study.sponsor, json_data['sponsor'])
        self.assertEqual(study.ind_number, json_data['ind_number'])

    def test_delete_study(self):
        self.add_studies()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow = self.create_workflow('file_and_email', study=study)
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        file_model = UserFileService.add_workflow_file(workflow_id=workflow.id,
                                                       irb_doc_code='Study_Protocol_Document',
                                                       task_spec_name=task.name,
                                                       name="anything.png", content_type="text",
                                                       binary_data=b'1234')
        form_data = {'Study_Protocol_Document': {'id': file_model.id},
                     'ShortDesc': 'My Short Description'}
        self.complete_form(workflow, task, form_data)

        task_events = session.query(TaskEventModel).filter(TaskEventModel.study_id == study.id).all()
        self.assertEqual(2, len(task_events))
        files = session.query(FileModel).all()
        self.assertEqual(1, len(files))
        emails = session.query(EmailModel).all()
        self.assertEqual(1, len(emails))
        email_doc_codes = session.query(EmailDocCodesModel).all()
        self.assertEqual(1, len(email_doc_codes))

        rv = self.app.delete('/v1.0/study/%i' % study.id, headers=self.logged_in_headers())
        self.assert_success(rv)

        task_events = session.query(TaskEventModel).filter(TaskEventModel.study_id == study.id).all()
        self.assertEqual(0, len(task_events))
        files = session.query(FileModel).all()
        self.assertEqual(0, len(files))
        emails = session.query(EmailModel).all()
        self.assertEqual(0, len(emails))
        email_doc_codes = session.query(EmailDocCodesModel).all()
        self.assertEqual(0, len(email_doc_codes))

    def test_delete_workflow(self):

        self.load_test_spec('random_fact')
        self.load_test_spec('empty_workflow', master_spec=True)
        self.add_test_study()
        workflow = session.query(WorkflowModel).first()
        UserFileService.add_workflow_file(workflow_id=workflow.id, task_spec_name='TaskSpec01',
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


    def test_delete_study_with_workflow_and_status_etc(self):

        self.load_test_spec('random_fact')
        self.load_test_spec('empty_workflow', master_spec=True)
        self.add_test_study()
        workflow = session.query(WorkflowModel).first()
        stats1 = StudyEvent(
            study_id=workflow.study_id,
            status=StudyStatus.in_progress,
            comment='Some study status change event',
            event_type=StudyEventType.user,
            user_uid=self.users[0]['uid'],
        )
        LdapService.user_info('dhf8r') # Assure that there is a dhf8r in ldap for StudyAssociated.

        email = EmailModel(subject="x", study_id=workflow.study_id)
        associate = StudyAssociated(study_id=workflow.study_id, uid=self.users[0]['uid'])
        event = StudyEvent(study_id=workflow.study_id)
        session.add_all([email, associate, event])


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
    #     ()
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


from datetime import datetime
import json
import unittest

from crc import db
from crc.models.study import StudyModel, StudyModelSchema, ProtocolBuilderStatus
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus, \
    WorkflowModelSchema, TaskSchema
from tests.base_test import BaseTest


class TestStudy(BaseTest, unittest.TestCase):

    def test_study_basics(self):
        self.load_example_data()
        study = db.session.query(StudyModel).first()
        self.assertIsNotNone(study)

    def test_add_study(self):
        study = {
            "id": 12345,
            "title": "Phase III Trial of Genuine People Personalities (GPP) Autonomous Intelligent Emotional Agents for Interstellar Spacecraft",
            "last_updated": datetime.now(),
            "protocol_builder_status": ProtocolBuilderStatus.in_process,
            "primary_investigator_id": "tricia.marie.mcmillan@heartofgold.edu",
            "sponsor": "Sirius Cybernetics Corporation",
            "ind_number": "567890",
        }
        rv = self.app.post('/v1.0/study',
                           content_type="application/json",
                           data=json.dumps(StudyModelSchema().dump(study)))
        self.assert_success(rv)
        db_study = db.session.query(StudyModel).first()
        self.assertIsNotNone(db_study)
        self.assertEqual(study["id"], db_study.id)
        self.assertEqual(study["title"], db_study.title)
        self.assertEqual(study["last_updated"], db_study.last_updated)
        self.assertEqual(study["protocol_builder_status"], db_study.protocol_builder_status)
        self.assertEqual(study["primary_investigator_id"], db_study.primary_investigator_id)
        self.assertEqual(study["sponsor"], db_study.sponsor)
        self.assertEqual(study["ind_number"], db_study.ind_number)

    def test_update_study(self):
        self.load_example_data()
        study: StudyModel = db.session.query(StudyModel).first()
        study.title = "Pilot Study of Fjord Placement for Single Fraction Outcomes to Cortisol Susceptibility"
        study.protocol_builder_status = ProtocolBuilderStatus.complete

        rv = self.app.post('/v1.0/study',
                           content_type="application/json",
                           data=json.dumps(StudyModelSchema().dump(study)))
        self.assert_success(rv)
        db_study = db.session.query(StudyModel).first()
        self.assertIsNotNone(db_study)
        self.assertEqual(study.title, db_study.title)
        self.assertEqual(study.protocol_builder_status, db_study.protocol_builder_status)

    def test_study_api_get_single_study(self):
        self.load_example_data()
        study = db.session.query(StudyModel).first()
        rv = self.app.get('/v1.0/study/%i' % study.id,
                          follow_redirects=True,
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        study2 = StudyModelSchema().load(json_data, session=db.session)
        self.assertEqual(study, study2)
        self.assertEqual(study.id, study2.id)
        self.assertEqual(study.title, study2.title)
        self.assertEqual(study.last_updated, study2.last_updated)
        self.assertEqual(study.protocol_builder_status, study2.protocol_builder_status)
        self.assertEqual(study.primary_investigator_id, study2.primary_investigator_id)
        self.assertEqual(study.sponsor, study2.sponsor)
        self.assertEqual(study.ind_number, study2.ind_number)

    def test_list_workflow_specifications(self):
        self.load_example_data()
        spec = db.session.query(WorkflowSpecModel).first()
        rv = self.app.get('/v1.0/workflow-specification',
                          follow_redirects=True,
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        specs = WorkflowSpecModelSchema(many=True).load(json_data, session=db.session)
        spec2 = specs[0]
        self.assertEqual(spec.id, spec2.id)
        self.assertEqual(spec.display_name, spec2.display_name)
        self.assertEqual(spec.description, spec2.description)

    def test_add_new_workflow_specification(self):
        self.load_example_data();
        num_before = db.session.query(WorkflowSpecModel).count()
        spec = WorkflowSpecModel(id='make_cookies', display_name='Cooooookies', description='Om nom nom delicious cookies')
        rv = self.app.post('/v1.0/workflow-specification', content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(rv)
        db_spec = db.session.query(WorkflowSpecModel).filter_by(id='make_cookies').first()
        self.assertEqual(spec.display_name, db_spec.display_name)
        num_after = db.session.query(WorkflowSpecModel).count()
        self.assertEqual(num_after, num_before + 1)

    def test_add_workflow_to_study(self):
        self.load_example_data()
        study = db.session.query(StudyModel).first()
        self.assertEqual(0, db.session.query(WorkflowModel).count())
        spec = db.session.query(WorkflowSpecModel).first()
        rv = self.app.post('/v1.0/study/%i/workflows' % study.id, content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(rv)
        self.assertEqual(1, db.session.query(WorkflowModel).count())
        workflow = db.session.query(WorkflowModel).first()
        self.assertEqual(study.id, workflow.study_id)
        self.assertEqual(WorkflowStatus.user_input_required, workflow.status)
        self.assertIsNotNone(workflow.bpmn_workflow_json)
        self.assertEqual(spec.id, workflow.workflow_spec_id)

        json_data = json.loads(rv.get_data(as_text=True))
        workflow2 = WorkflowModelSchema().load(json_data, session=db.session)
        self.assertEqual(workflow.id, workflow2.id)

    def test_delete_workflow(self):
        self.load_example_data()
        study = db.session.query(StudyModel).first()
        spec = db.session.query(WorkflowSpecModel).first()
        rv = self.app.post('/v1.0/study/%i/workflows' % study.id, content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assertEqual(1, db.session.query(WorkflowModel).count())
        json_data = json.loads(rv.get_data(as_text=True))
        workflow = WorkflowModelSchema().load(json_data, session=db.session)
        rv = self.app.delete('/v1.0/workflow/%i' % workflow.id)
        self.assert_success(rv)
        self.assertEqual(0, db.session.query(WorkflowModel).count())

    def test_get_current_user_tasks(self):
        self.load_example_data()
        study = db.session.query(StudyModel).first()
        spec = db.session.query(WorkflowSpecModel).filter_by(id='random_fact').first()
        self.app.post('/v1.0/study/%i/workflows' % study.id, content_type="application/json",
                      data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        rv = self.app.get('/v1.0/workflow/%i/tasks' % study.id, content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        tasks = TaskSchema(many=True).load(json_data)
        self.assertEqual("Task_User_Select_Type", tasks[0].name)
        self.assertEqual(3, len(tasks[0].form["fields"][0]["options"]))

    def test_two_forms_task(self):
        # Set up a new workfllow
        self.load_example_data()
        study = db.session.query(StudyModel).first()
        spec = db.session.query(WorkflowSpecModel).filter_by(id='two_forms').first()
        rv = self.app.post('/v1.0/study/%i/workflows' % study.id, content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        json_data = json.loads(rv.get_data(as_text=True))
        workflow = WorkflowModelSchema().load(json_data, session=db.session)

        # get the first from in the two form workflow.
        rv = self.app.get('/v1.0/workflow/%i/tasks' % workflow.id, content_type="application/json")
        json_data = json.loads(rv.get_data(as_text=True))
        tasks = TaskSchema(many=True).load(json_data)
        self.assertEqual(1, len(tasks))
        self.assertIsNotNone(tasks[0].form)
        self.assertEqual("StepOne", tasks[0].name)
        self.assertEqual(1, len(tasks[0].form['fields']))

        # Complete the form for Step one and post it.
        tasks[0].form['fields'][0]['value']="Blue"
        rv = self.app.put('/v1.0/workflow/%i/task/%s' % (workflow.id, tasks[0].name), content_type="application/json",
                           data=json.dumps(TaskSchema().dump(tasks[0])))
        self.assert_success(rv)

        # Get the next Task
        rv = self.app.get('/v1.0/workflow/%i/tasks' % study.id, content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        tasks = TaskSchema(many=True).load(json_data)
        self.assertEqual("StepTwo", tasks[0].name)
        self.assertEqual(3, len(tasks[0].form["fields"][0]["options"]))

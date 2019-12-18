import json
import unittest
from crc import db
from crc.models import StudyModel, StudySchema, WorkflowSpecModel, WorkflowSpecSchema
from tests.base_test import BaseTest


class TestStudy(BaseTest, unittest.TestCase):

    def test_study_basics(self):
        self.load_example_data()
        study = db.session.query(StudyModel).first()
        self.assertIsNotNone(study)

    def test_study_api_get_single_study(self):
        self.load_example_data()
        study = db.session.query(StudyModel).first()
        rv = self.app.get('/v1.0/study/%i' % study.id,
                          follow_redirects=True,
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        study2 = StudySchema().load(json_data, session=db.session)
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
        specs = WorkflowSpecSchema(many=True).load(json_data, session=db.session)
        spec2 = specs[0]
        self.assertEqual(spec.id, spec2.id)
        self.assertEqual(spec.display_name, spec2.display_name)
        self.assertEqual(spec.description, spec2.description)

    def test_add_workflow_to_study(self):
        self.load_example_data()
        study = db.session.query(StudyModel).first()
        spec = db.session.query(WorkflowSpecModel).first()
        rv = self.app.post('/v1.0/study/%i/workflows' % study.id,content_type="application/json",
                           data=json.dumps(WorkflowSpecSchema().dump(spec)))
        self.assert_success(rv)



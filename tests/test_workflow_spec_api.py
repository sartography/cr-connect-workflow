import json
from datetime import datetime, tzinfo, timezone

from crc import session
from crc.models.file import FileModel
from crc.models.study import StudyModel, StudyModelSchema, ProtocolBuilderStatus
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus, \
    WorkflowApiSchema
from tests.base_test import BaseTest


class TestWorkflowSpec(BaseTest):

    def test_list_workflow_specifications(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        rv = self.app.get('/v1.0/workflow-specification',
                          follow_redirects=True,
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        specs = WorkflowSpecModelSchema(many=True).load(json_data, session=session)
        spec2 = specs[0]
        self.assertEqual(spec.id, spec2.id)
        self.assertEqual(spec.display_name, spec2.display_name)
        self.assertEqual(spec.description, spec2.description)

    def test_add_new_workflow_specification(self):
        self.load_example_data();
        num_before = session.query(WorkflowSpecModel).count()
        spec = WorkflowSpecModel(id='make_cookies', display_name='Cooooookies',
                                 description='Om nom nom delicious cookies')
        rv = self.app.post('/v1.0/workflow-specification', content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(rv)
        db_spec = session.query(WorkflowSpecModel).filter_by(id='make_cookies').first()
        self.assertEqual(spec.display_name, db_spec.display_name)
        num_after = session.query(WorkflowSpecModel).count()
        self.assertEqual(num_after, num_before + 1)

    def test_get_workflow_specification(self):
        self.load_example_data()
        db_spec = session.query(WorkflowSpecModel).first()
        rv = self.app.get('/v1.0/workflow-specification/%s' % db_spec.id)
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        api_spec = WorkflowSpecModelSchema().load(json_data, session=session)
        self.assertEqual(db_spec, api_spec)

    def test_delete_workflow_specification(self):
        self.load_example_data()
        spec_id = 'random_fact'

        num_specs_before = session.query(WorkflowSpecModel).filter_by(id=spec_id).count()
        self.assertEqual(num_specs_before, 1)

        num_files_before = session.query(FileModel).filter_by(workflow_spec_id=spec_id).count()
        num_workflows_before = session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id).count()
        self.assertGreater(num_files_before + num_workflows_before, 0)

        rv = self.app.delete('/v1.0/workflow-specification/' + spec_id)
        self.assert_success(rv)

        num_specs_after = session.query(WorkflowSpecModel).filter_by(id=spec_id).count()
        self.assertEqual(0, num_specs_after)

        # Make sure that all items in the database with the workflow spec ID are deleted as well.
        num_files_after = session.query(FileModel).filter_by(workflow_spec_id=spec_id).count()
        num_workflows_after = session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id).count()
        self.assertEqual(num_files_after + num_workflows_after, 0)

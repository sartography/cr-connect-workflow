import json
from datetime import datetime

from crc import session
from crc.models.file import FileModel
from crc.models.study import StudyModel, StudyModelSchema, ProtocolBuilderStatus
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus, \
    WorkflowModelSchema, TaskSchema
from tests.base_test import BaseTest


class TestTasksApi(BaseTest):

    def create_workflow(self, workflow_name):
        study = session.query(StudyModel).first()
        spec = session.query(WorkflowSpecModel).filter_by(id=workflow_name).first()
        self.app.post('/v1.0/study/%i/workflows' % study.id, content_type="application/json",
                      data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        workflow = session.query(WorkflowModel).filter_by(study_id = study.id, workflow_spec_id=workflow_name).first()
        return workflow

    def get_tasks(self, workflow):
        rv = self.app.get('/v1.0/workflow/%i/tasks' % workflow.id, content_type="application/json")
        json_data = json.loads(rv.get_data(as_text=True))
        tasks = TaskSchema(many=True).load(json_data)
        return tasks

    def get_all_tasks(self, workflow):
        rv = self.app.get('/v1.0/workflow/%i/all_tasks' % workflow.id, content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        all_tasks = TaskSchema(many=True).load(json_data)
        return all_tasks

    def complete_form(self, workflow, task, dict_data):
        rv = self.app.put('/v1.0/workflow/%i/task/%s/data' % (workflow.id, task.id),
                          content_type="application/json",
                          data=json.dumps(dict_data))
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        workflow = WorkflowModelSchema().load(json_data, session=session)
        return workflow

    def test_get_current_user_tasks(self):
        self.load_example_data()
        workflow = self.create_workflow('random_fact')
        tasks = self.get_tasks(workflow)
        self.assertEqual("Task_User_Select_Type", tasks[0].name)
        self.assertEqual(3, len(tasks[0].form["fields"][0]["options"]))

    def test_two_forms_task(self):
        # Set up a new workflow
        self.load_example_data()
        workflow = self.create_workflow('two_forms')
        # get the first form in the two form workflow.
        tasks = self.get_tasks(workflow)
        self.assertEqual(1, len(tasks))
        self.assertIsNotNone(tasks[0].form)
        self.assertEqual("StepOne", tasks[0].name)
        self.assertEqual(1, len(tasks[0].form['fields']))

        # Complete the form for Step one and post it.
        self.complete_form(workflow, tasks[0], {"color": "blue"})

        # Get the next Task
        tasks = self.get_tasks(workflow)
        self.assertEqual("StepTwo", tasks[0].name)

        # Get all user Tasks and check that the data have been saved
        all_tasks = self.get_all_tasks(workflow)
        for task in all_tasks:
            self.assertIsNotNone(task.data)
            for val in task.data.values():
                self.assertIsNotNone(val)

    def test_error_message_on_bad_gateway_expression(self):
        self.load_example_data()
        workflow = self.create_workflow('exclusive_gateway')

        # get the first form in the two form workflow.
        tasks = self.get_tasks(workflow)
        self.complete_form(workflow, tasks[0], {"has_bananas": True})


    def test_workflow_with_parallel_forms(self):
        self.load_example_data()
        workflow = self.create_workflow('exclusive_gateway')

        # get the first form in the two form workflow.
        tasks = self.get_tasks(workflow)
        self.complete_form(workflow, tasks[0], {"has_bananas": True})

        # Get the next Task
        tasks = self.get_tasks(workflow)
        self.assertEqual("Task_Why_No_Bananas", tasks[0].name)

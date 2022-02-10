import json

from tests.base_test import BaseTest

from crc.models.user import UserModel
from crc import session, WorkflowService
from crc.models.api_models import Task, TaskSchema
from crc.models.task_log import TaskLogModel, TaskLogModelSchema, TaskLogQuery, TaskLogQuerySchema
from crc.models.study import StudyModel
from crc.scripts.log import TaskLog
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.task_logging_service import TaskLoggingService

import types


class TestTaskLogging(BaseTest):

    def test_logging_validation(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('logging_task')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_add_log(self):
        workflow = self.create_workflow('logging_task')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        log_id = task.data['log_model']['id']
        log_model = session.query(TaskLogModel).filter(TaskLogModel.id == log_id).first()

        self.assertEqual('test_code', log_model.code)
        self.assertEqual('info', log_model.level)
        self.assertEqual('Activity_LogEvent', log_model.task)

    def test_get_logging_validation(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('get_logging')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_get_logs(self):
        workflow = self.create_workflow('get_logging')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.assertEqual(2, len(task.data['logging_models_all_post']))
        self.assertEqual(1, len(task.data['logging_models_info_post']))
        self.assertEqual(1, len(task.data['logging_models_debug_post']))
        self.assertIn(task.data['logging_models_info_post'][0], task.data['logging_models_all_post'])
        self.assertIn(task.data['logging_models_debug_post'][0], task.data['logging_models_all_post'])
        self.assertEqual('test_code', task.data['logging_models_info_post'][0]['code'])
        self.assertEqual('debug_test_code', task.data['logging_models_debug_post'][0]['code'])

    def test_get_logs_for_study(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow = self.create_workflow('hello_world', study=study)
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()

        TaskLog().do_task(task, study.id, workflow.id,
                           level='critical',
                           code='critical_code',
                           message='This is my critical message.')

        TaskLog().do_task(task, study.id, workflow.id,
                           level='debug',
                           code='debug_code',
                           message='This is my debug message.')

        # This workflow adds 3 logs
        # some_text = 'variable'
        # log('info', 'some_code', 'Some longer message')
        # log('info', 'some_other_code', 'Another really long message')
        # log('debug', 'debug_code', f'This message has a { some_text }!')
        workflow = self.create_workflow('get_logging_for_study', study=study)
        workflow_api = self.get_workflow_api(workflow)
        task_api = workflow_api.next_task
        workflow_api = self.complete_form(workflow, task_api, {})
        task_api = workflow_api.next_task
        workflow_logs = task_api.data['workflow_logs']
        study_logs = task_api.data['study_logs']
        self.assertEqual(3, len(workflow_logs))
        self.assertEqual(5, len(study_logs))

    def test_logging_api(self):
        workflow = self.create_workflow('logging_task')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        user = session.query(UserModel).filter_by(uid=self.test_uid).first()
        url = f'/v1.0/study/{workflow.study_id}/log'
        task_log_query = TaskLogQuery()
        rv = self.app.put(url, headers=self.logged_in_headers(user), content_type="application/json",
                          data=TaskLogQuerySchema().dump(task_log_query))
        self.assert_success(rv)
        log_query = json.loads(rv.get_data(as_text=True))
        logs = log_query['items']
        self.assertEqual(1, len(logs))
        self.assertEqual(workflow.id, logs[0]['workflow_id'])
        self.assertEqual(workflow.study_id, logs[0]['study_id'])
        self.assertEqual('info', logs[0]['level'])
        self.assertEqual(self.test_uid, logs[0]['user_uid'])
        self.assertEqual('You forgot to include the correct data.', logs[0]['message'])

        url = f'/v1.0/workflow/{workflow.id}/log'
        rv = self.app.put(url, headers=self.logged_in_headers(user), content_type="application/json",
                          data=TaskLogQuerySchema().dump(task_log_query))

        self.assert_success(rv)
        wf_logs = json.loads(rv.get_data(as_text=True))['items']
        self.assertEqual(wf_logs, logs, "Logs returned for the workflow should be identical to those returned from study")

    def test_logging_service_paginates_and_sorts(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_model = self.create_workflow('hello_world', study=study)
        workflow_processor = WorkflowProcessor(workflow_model)
        task = workflow_processor.next_task()

        for i in range(0, 10):
            TaskLog().do_task(task, study.id, workflow_model.id, level='critical', code='critical_code',
                              message=f'This is my critical message # {i}.')
            TaskLog().do_task(task, study.id, workflow_model.id, level='debug', code='debug_code',
                              message=f'This is my debug message # {i}.')
            TaskLog().do_task(task, study.id, workflow_model.id, level='error', code='debug_code',
                              message=f'This is my error message # {i}.')
            TaskLog().do_task(task, study.id, workflow_model.id, level='info', code='debug_code',
                              message=f'This is my info message # {i}.')

        results = TaskLoggingService.get_logs_for_study(study.id, TaskLogQuery(per_page=100))
        self.assertEqual(40, len(results.items), "There should be 40 logs total")

        logs = TaskLoggingService.get_logs_for_study(study.id, TaskLogQuery(per_page=5))
        self.assertEqual(40, logs.total)
        self.assertEqual(5, len(logs.items), "I can limit results to 5")
        self.assertEqual(1, logs.page)
        self.assertEqual(8, logs.pages)
        self.assertEqual(5, logs.per_page)
        self.assertEqual(True, logs.has_next)
        self.assertEqual(False, logs.has_prev)

        logs = TaskLoggingService.get_logs_for_study(study.id, TaskLogQuery(per_page=5, sort_column="level"))
        for i in range(0, 5):
            self.assertEqual('critical', logs.items[i].level, "It is possible to sort on a column")

        logs = TaskLoggingService.get_logs_for_study(study.id, TaskLogQuery(per_page=5, sort_column="level", sort_reverse=True))
        for i in range(0, 5):
            self.assertEqual('info', logs.items[i].level, "It is possible to sort on a column")
from tests.base_test import BaseTest

from crc import session
from crc.models.api_models import Task
from crc.models.task_log import TaskLogModel
from crc.models.study import StudyModel
from crc.scripts.log import MyScript

import types


class TestTaskLogging(BaseTest):

    def test_add_log(self):
        workflow = self.create_workflow('logging_task')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        log_id = task.data['log_model']['id']
        log_model = session.query(TaskLogModel).filter(TaskLogModel.id == log_id).first()

        self.assertEqual('test_code', log_model.code)
        self.assertEqual('info', log_model.level)
        self.assertEqual('Activity_LogEvent', log_model.task)

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
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        task_model = Task(id=task.id,
                          name=task.name,
                          title=task.title,
                          type=task.type,
                          state=task.state,
                          lane=task.lane,
                          form=task.form,
                          documentation=task.documentation,
                          data=task.data,
                          multi_instance_type=task.multi_instance_type,
                          multi_instance_count=task.multi_instance_count,
                          multi_instance_index=task.multi_instance_index,
                          process_name=task.process_name,
                          properties=task.properties)

        task_model.get_name = types.MethodType(lambda x: x.name, task_model)

        MyScript().do_task(task_model, study.id, workflow.id,
                           level='critical',
                           code='critical_code',
                           message='This is my critical message.')

        MyScript().do_task(task_model, study.id, workflow.id,
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
        task = workflow_api.next_task
        workflow_api = self.complete_form(workflow, task, {})
        task = workflow_api.next_task
        workflow_logs = task.data['workflow_logs']
        study_logs = task.data['study_logs']
        self.assertEqual(3, len(workflow_logs))
        self.assertEqual(5, len(study_logs))

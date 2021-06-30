import json
import time

from crc.services.workflow_processor import WorkflowProcessor
from tests.base_test import BaseTest
from crc.models.workflow import WorkflowStatus, WorkflowModel
from crc import db
from crc.api.common import ApiError
from crc.models.task_event import TaskEventModel, TaskEventSchema
from crc.services.workflow_service import WorkflowService


class TestTimerEvent(BaseTest):


    def test_timer_event(self):
        workflow = self.create_workflow('timer_event')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        processor.complete_task(task)
        tasks = processor.get_ready_user_tasks()
        self.assertEqual(tasks,[])
        processor.save()
        time.sleep(.3) # our timer is at .25 sec so we have to wait for it
                       # get done waiting
        WorkflowService.do_waiting()
        wf = db.session.query(WorkflowModel).filter(WorkflowModel.id == workflow.id).first()
        self.assertTrue(wf.status != WorkflowStatus.waiting)


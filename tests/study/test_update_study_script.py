from tests.base_test import BaseTest

from crc.scripts.update_study import UpdateStudy
from crc.services.workflow_processor import WorkflowProcessor


class TestUpdateStudyScript(BaseTest):

    def test_do_task(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        task.data = {"details": {
            "label": "My New Title",
            "value": "dhf8r"}
        }

        script = UpdateStudy()
        script.do_task(task, workflow.study_id, workflow.id, "title:details.label", "pi:details.value")
        self.assertEqual("My New Title", workflow.study.title)
        self.assertEqual("dhf8r", workflow.study.primary_investigator_id)

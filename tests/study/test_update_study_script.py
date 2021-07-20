from tests.base_test import BaseTest

from crc.scripts.update_study import UpdateStudy
from crc.services.workflow_processor import WorkflowProcessor
from SpiffWorkflow.bpmn.PythonScriptEngine import Box


class TestUpdateStudyScript(BaseTest):

    def test_do_task(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        details = Box({
            "label": "My New Title",
            "short": "My New Short Title",
            "value": "dhf8r"})


        script = UpdateStudy()
        # note that we changed where the argument gets evaluated
        # previsously, it took the arguments and then evaluated them within the script
        # now, it evaluates the arugments in the context of the main script so they get
        # evaluated before they are passed to the script -
        # this allows us to do a lot more things like strings, functions, etc.
        # and it makes the arguments less confusing to use.
        script.do_task(task, workflow.study_id, workflow.id, title = details.label,
                                                             short_title = details.short,
                                                             pi = details.value)
        self.assertEqual("My New Title", workflow.study.title)
        self.assertEqual("My New Short Title", workflow.study.short_title)
        self.assertEqual("dhf8r", workflow.study.primary_investigator_id)

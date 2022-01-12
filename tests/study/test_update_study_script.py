from tests.base_test import BaseTest

from crc.scripts.update_study import UpdateStudy
from crc.services.workflow_processor import WorkflowProcessor
from SpiffWorkflow.bpmn.PythonScriptEngine import Box


class TestUpdateStudyScript(BaseTest):

    def test_do_task(self):
        self.load_example_data()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        details = Box({
            "title": "My New Title",
            "short_title": "My New Short Title",
            "pi": "dhf8r",
            "short_name": "My Short Name",
            "proposal_name": "My Proposal Name"
        })


        script = UpdateStudy()
        # note that we changed where the argument gets evaluated
        # previsously, it took the arguments and then evaluated them within the script
        # now, it evaluates the arugments in the context of the main script so they get
        # evaluated before they are passed to the script -
        # this allows us to do a lot more things like strings, functions, etc.
        # and it makes the arguments less confusing to use.
        script.do_task(task, workflow.study_id, workflow.id,
                       title=details.title,
                       short_title=details.short_title,
                       pi=details.pi,
                       short_name=details.short_name,
                       proposal_name=details.proposal_name)
        self.assertEqual(details.title, workflow.study.title)
        self.assertEqual(details.short_title, workflow.study.short_title)
        self.assertEqual(details.pi, workflow.study.primary_investigator_id)
        self.assertEqual(details.short_name, workflow.study.short_name)
        self.assertEqual(details.proposal_name, workflow.study.proposal_name)

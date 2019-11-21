from __future__ import print_function
from SpiffWorkflow.specs import WorkflowSpec, ExclusiveChoice, Simple, Cancel
from SpiffWorkflow.operators import Equal, Attrib


import json
from SpiffWorkflow import Workflow
from SpiffWorkflow.specs import WorkflowSpec
from SpiffWorkflow.serializer.json import JSONSerializer

# Load from JSON
with open('nuclear.json') as fp:
    workflow_json = fp.read()
serializer = JSONSerializer()
spec = WorkflowSpec.deserialize(serializer, workflow_json)

# Create the workflow.
workflow = Workflow(spec)

# Execute until all tasks are done or require manual intervention.
# For the sake of this tutorial, we ignore the "manual" flag on the
# tasks. In practice, you probably don't want to do that.
workflow.complete_all(halt_on_manual=False)

# Alternatively, this is what a UI would do for a manual task.
#workflow.complete_task_from_id(...)


def my_nuclear_strike(msg):
    print("Launched:", msg)


class NuclearStrikeWorkflowSpec(WorkflowSpec):
    def __init__(self):
        WorkflowSpec.__init__(self)

        # The first step of our workflow is to let the general confirm
        # the nuclear strike.
        general_choice = ExclusiveChoice(self, 'general')
        self.start.connect(general_choice)

        # The default choice of the general is to abort.
        cancel = Cancel(self, 'workflow_aborted')
        general_choice.connect(cancel)

        # Otherwise, we will ask the president to confirm.
        president_choice = ExclusiveChoice(self, 'president')
        cond = Equal(Attrib('confirmation'), 'yes')
        general_choice.connect_if(cond, president_choice)

        # The default choice of the president is to abort.
        president_choice.connect(cancel)

        # Otherwise, we will perform the nuclear strike.
        strike = Simple(self, 'nuclear_strike')
        president_choice.connect_if(cond, strike)

        # Now we connect our Python function to the Task named 'nuclear_strike'
        strike.completed_event.connect(my_nuclear_strike)

        # As soon as all tasks are either "completed" or  "aborted", the
        # workflow implicitely ends.


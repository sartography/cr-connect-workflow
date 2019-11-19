from SpiffWorkflow.operators import Equal, Attrib
from SpiffWorkflow.specs import WorkflowSpec, ExclusiveChoice, Simple, Cancel


def send_message(msg):
    print("Training Workflow Started:", msg)


class TrainingWorkflowSpec(WorkflowSpec):
    def __init__(self):
        WorkflowSpec.__init__(self)

        coordinator_choice = ExclusiveChoice(self, 'coordinator')
        self.start.connect(coordinator_choice)

        cancel = Cancel(self, 'workflow_canceled')
        coordinator_choice.connect(cancel)

        dept_chair_choice = ExclusiveChoice(self, 'dept_chair')
        cond = Equal(Attrib('confirmation'), 'yes')
        coordinator_choice.connect_if(cond, dept_chair_choice)

        dept_chair_choice.connect(cancel)

        approve = Simple(self, 'approve_study')
        dept_chair_choice.connect_if(cond, approve)

        approve.completed_event.connect(send_message)

import json
from cmd import Cmd

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.serializer.json import JSONSerializer
from flask import jsonify

from app.model.WorkflowRunner import WorkflowRunner


class MyPrompt(Cmd):


    def __init__(self):
        super().__init__()
        runner = WorkflowRunner('../static/bpmn/joke.bpmn', debug=False)
        spec = runner.get_spec()
        self.workflow = BpmnWorkflow(spec)

        self.workflow.debug = False
        serializer = JSONSerializer()
        data = self.workflow.serialize(serializer)
        self.pretty = json.dumps(json.loads(data), indent=4, separators=(',', ': '))


    def do_hello(self, args):
        """Says hello. If you provide a name, it will greet you with it."""
        if len(args) == 0:
            name = 'stranger'
        else:
            name = args
        print("Hello, %s" % name)

    def do_quit(self, args):
        """Quits the program."""
        print("Quitting.")
        raise SystemExit

    def do_debug(self, args):
        """Prints the full task tree."""
        print(self.pretty)

    def do_engine(self, args):
        """Completes any tasks that are engine specific, completes until there are
        only READY user tasks, or WAITING tasks available. """
        self.workflow.do_engine_steps()

    def do_complete_all(self, args):
        """Completes everything that is possible to complete"""
        self.workflow.complete_all()

    def do_ready(self, args):
        """Prints a list of user tasks that are ready for action."""
        ready_tasks = self.workflow.get_ready_user_tasks()
        print("The following task ids are ready for execution:")
        for task in ready_tasks:
            print("\t" + str(task.id) + " : " + str(task.get_name()))

    def do_waiting(self, args):
        """Prints a list of tasks that are in the waiting state."""
        tasks = self.workflow.get_waiting_tasks()
        print("The following task ids are waiting for exectution:")
        for task in tasks:
            print("\t" + str(task.id) + " : " + str(task.get_name()))

    def do_next(self, args):
        """Attempts to do the next task."""
        print("Running the next task")
        self.workflow.complete_next(pick_up=True, halt_on_manual=True)
        tasks = self.workflow.get_waiting_tasks()
        print("Next Tasks:")
        for task in tasks:
            print("\t" + str(task.get_name()))

    def do_answer(self, args):
        tasks = self.workflow.get_ready_user_tasks()
        if len(tasks) == 1:
            print("You answered " + args)
            data = {}
            data["answer"] = args
            tasks[0].set_data(**data)


if __name__ == '__main__':
    prompt = MyPrompt()
    prompt.prompt = '> '
    prompt.cmdloop('Starting prompt...')

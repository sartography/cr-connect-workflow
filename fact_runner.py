import pprint

from SpiffWorkflow.bpmn.BpmnScriptEngine import BpmnScriptEngine
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.camunda.serializer.CamundaSerializer import CamundaSerializer
from SpiffWorkflow.camunda.specs.UserTask import EnumFormField, UserTask


class CustomBpmnScriptEngine(BpmnScriptEngine):
    """This is a custom script processor that can be easily injected into Spiff Workflow.
    Rather than execute arbitrary code, this assumes the script references a fully qualified python class
    such as myapp.RandomFact. """

    def execute(self, task, script, **kwargs):
        """
        Assume that the script read in from the BPMN file is a fully qualified python class. Instantiate
        that class, pass in any data available to the current task so that it might act on it.
        Assume that the class implements the "do_task" method.

        This allows us to reference custom code from the BPMN diagram.
        """
        module_name = "app." + script
        class_name = module_name.split(".")[-1]
        mod = __import__(module_name, fromlist=[class_name])
        klass = getattr(mod, class_name)
        klass().do_task(task.data)

def main():
    print("Loading BPMN Specification.")
    spec = bpmn_diagram_to_spec('app/static/bpmn/random_fact')

    print ("Creating a new workflow based on the specification.")
    script_engine = CustomBpmnScriptEngine()
    workflow = BpmnWorkflow(spec, script_engine=script_engine)
    workflow.debug = False

    print ("Running automated tasks.")
    workflow.do_engine_steps()

    while not workflow.is_completed():
        workflow.do_engine_steps()
        ready_tasks = workflow.get_ready_user_tasks()
        while len(ready_tasks) > 0:
            for task in ready_tasks:
                if isinstance(task.task_spec, UserTask):
                    show_form(task)
                    workflow.complete_next()
                else:
                    raise("Unown Ready Task.")
            workflow.do_engine_steps()
            ready_tasks = workflow.get_ready_user_tasks()

    print("All tasks in the workflow are now complete.")
    print("The following data was collected:")
    pprint.pprint(workflow.last_task.data)

def show_form(task):
    model = {}
    form = task.task_spec.form
    for field in form.fields:
        print("Please complete the following questions:")
        prompt = field.label
        if isinstance(field, EnumFormField):
            prompt += "? (Options: " + ', '.join([str(option.id) for option in field.options]) + ")"
        prompt += "? "
        model[form.key + "." + field.id] = input(prompt)
    if task.data is None:
        task.data = {}
    task.data.update(model)


def bpmn_diagram_to_spec(file_path):
    """This loads up all BPMN diagrams in the BPMN folder."""
    workflowSpec = CamundaSerializer().deserialize_workflow_spec(file_path)
    return workflowSpec


if __name__ == "__main__":
    main()

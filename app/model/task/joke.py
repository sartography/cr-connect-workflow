from SpiffWorkflow.bpmn.serializer.BpmnSerializer import BpmnSerializer
from SpiffWorkflow.serializer.json import JSONSerializer
from SpiffWorkflow.specs import Simple


class Joke(Simple):
    def _on_trigger(self, my_task):
        pass

    def _on_complete_hook(self, my_task):
        print("This is a Joke Task!")

    def serialize(self, serializer):
        return serializer.serialize_nuclear_strike(self)

    @classmethod
    def deserialize(cls, serializer, wf_spec, s_state):
        return serializer.deserialize_nuclear_strike(wf_spec, s_state)


class JokeSerializer(BpmnSerializer):
    def serialize_nuclear_strike(self, task_spec):
        return self.serialize_task_spec(task_spec)

    def deserialize_nuclear_strike(self, wf_spec, s_state):
        spec = Joke(wf_spec, s_state['name'])
        self.deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec



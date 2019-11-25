from SpiffWorkflow.bpmn.serializer.BpmnSerializer import BpmnSerializer
from SpiffWorkflow.serializer.json import JSONSerializer
from SpiffWorkflow.specs import Simple


class TellJoke(Simple):
    def _on_trigger(self, my_task):
        print("What has a face and two hands but no arms or legs?")
        pass

    def _on_complete_hook(self, my_task):
        pass

    def serialize(self, serializer):
        return serializer.serialize_joke(self)

    @classmethod
    def deserialize(cls, serializer, wf_spec, s_state):
        return serializer.deserialize_joke(wf_spec, s_state)


class TellJokeSerializer(BpmnSerializer):
    def serialize_joke(self, task_spec):
        return self.serialize_task_spec(task_spec)

    def deserialize_joke(self, wf_spec, s_state):
        spec = TellJoke(wf_spec, s_state['name'])
        self.deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec



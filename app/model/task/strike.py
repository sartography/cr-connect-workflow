from SpiffWorkflow.serializer.json import JSONSerializer
from SpiffWorkflow.specs import Simple


class NuclearStrike(Simple):
    def _on_complete_hook(self, my_task):
        print("The Rocket is Sent!")

    def serialize(self, serializer):
        return serializer.serialize_nuclear_strike(self)

    @classmethod
    def deserialize(cls, serializer, wf_spec, s_state):
        return serializer.deserialize_nuclear_strike(wf_spec, s_state)


class NuclearSerializer(JSONSerializer):
    def serialize_nuclear_strike(self, task_spec):
        return self.serialize_task_spec(task_spec)

    def deserialize_nuclear_strike(self, wf_spec, s_state):
        spec = NuclearStrike(wf_spec, s_state['name'])
        self.deserialize_task_spec(wf_spec, s_state, spec=spec)
        return spec



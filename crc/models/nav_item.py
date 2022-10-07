from SpiffWorkflow.bpmn.specs.BpmnSpecMixin import BpmnSpecMixin, SequenceFlow


class NavItem(object):
    """
        A waypoint in a workflow along with some key metrics
        - Each list item has :
           spec_id          -   TaskSpec or Sequence flow id
           name             -   The name of the task spec (or sequence)
           spec_type        -   The type of task spec (it's class name)
           task_id          -   The uuid of the actual task instance, if it exists
           description      -   Text description
           backtrack_to     -   The spec_id of the task this will back track to.
           indent           -   A hint for indentation
           lane             -   This is the lane for the task if indicated.
           state            -   State of the task
    """

    def __init__(self, spec_id, name, description, spec_type,
                 lane=None, backtrack_to=None, indent=0):
        self.spec_id = spec_id
        self.name = name
        self.spec_type = "None"
        self.description = description
        self.lane = lane
        self.backtrack_to = backtrack_to
        self.indent = indent
        self.task_id = None
        self.state = None
        self.children = []

    @classmethod
    def from_spec(cls, spec: BpmnSpecMixin, backtrack_to=None, indent=None):
        instance = cls(
            spec_id=spec.id,
            name=spec.name,
            description=spec.description,
            spec_type=spec.spec_type,
            lane=spec.lane,
            backtrack_to=backtrack_to,
            indent=indent,
        )

        return instance

    @classmethod
    def from_flow(cls, flow: SequenceFlow, lane, backtrack_to, indent):
        """We include flows in the navigation if we hit a conditional gateway,
        as in do this if x, do this if y...."""
        instance = cls(
            spec_id=flow.id,
            name=flow.name,
            description=flow.name,
            lane=lane,
            backtrack_to=backtrack_to,
            indent=indent
        )
        instance.set_spec_type(flow)
        return instance

    def __eq__(self, other):
        if isinstance(other, NavItem):
            return self.spec_id == other.spec_id and \
                   self.name == other.name and \
                   self.spec_type == other.spec_type and \
                   self.description == other.description and \
                   self.lane == other.lane and \
                   self.backtrack_to == other.backtrack_to and \
                   self.indent == other.indent
        return False

    def __str__(self):
        text = self.description
        if self.spec_type == "StartEvent":
            text = "O"
        elif self.spec_type == "TaskEndEvent":
            text = "@"
        elif self.spec_type == "ExclusiveGateway":
            text = f"X {text} X"
        elif self.spec_type == "ParallelGateway":
            text = f"+ {text}"
        elif self.spec_type == "SequenceFlow":
            text = f"-> {text}"
        elif self.spec_type[-4:] == "Task":
            text = f"[{text}] TASK ID: {self.task_id}"
        else:
            text = f"({self.spec_type}) {text}"

        result = f' {"..," * self.indent} STATE: {self.state} {text}'
        if self.lane:
            result = f'|{self.lane}| {result}'
        if self.backtrack_to:
            result += f"  (BACKTRACK to {self.backtrack_to}"

        return result
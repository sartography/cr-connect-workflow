from SpiffWorkflow.exceptions import WorkflowTaskExecException

from crc.scripts.script import Script
from crc.api.common import ApiError

from crc.services.protocol_builder import ProtocolBuilderService


class IRBInfo(Script):

    pb = ProtocolBuilderService()

    def get_description(self):
        return """Returns the IRB Info data for a Study"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return isinstance(study_id, int)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        irb_info = self.pb.get_irb_info(study_id)
        if irb_info:
            return irb_info
        else:
            raise WorkflowTaskExecException(task, f'get_irb_info failed.  There was a problem retrieving IRB Info'
                                                  f' for study {study_id}.')
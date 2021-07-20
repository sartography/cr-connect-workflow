from crc.scripts.script import Script
from crc.services.failing_service import FailingService


class FailingScript(Script):

    def get_description(self):
        return """It fails"""

    def do_task_validate_only(self, task, *args, **kwargs):
        pass

    def do_task(self, task, *args, **kwargs):

        FailingService.fail_as_service()
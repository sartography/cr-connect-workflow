from crc.api.common import ApiError


class Script:
    """ Provides an abstract class that defines how scripts should work, this
    must be extended in all Script Tasks."""

    def get_description(self):
        raise ApiError("invalid_script",
                       "This script does not supply a description.")

    def do_task(self, task, study_id, **kwargs):
        raise ApiError("invalid_script",
                       "This is an internal error. The script you are trying to execute " +
                       "does not properly implement the do_task function.")

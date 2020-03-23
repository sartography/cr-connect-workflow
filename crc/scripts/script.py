import importlib
import os
import pkgutil

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

    def validate(self):
        """Override this method to perform an early check that the script has access to
        everything it needs to properly process requests.
        Should return an array of ScriptValidationErrors.
        """
        return []

    @staticmethod
    def get_all_subclasses():
        return Script._get_all_subclasses(Script)

    @staticmethod
    def _get_all_subclasses(cls):

        # hackish mess to make sure we have all the modules loaded for the scripts
        pkg_dir = os.path.dirname(__file__)
        for (module_loader, name, ispkg) in pkgutil.iter_modules([pkg_dir]):
            importlib.import_module('.' + name, __package__)


        """Returns a list of all classes that extend this class."""
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(Script._get_all_subclasses(subclass))

        return all_subclasses


class ScriptValidationError:

    def __init__(self, code, message):
        self.code = code
        self.message = message

    @classmethod
    def from_api_error(cls, api_error: ApiError):
        return cls(api_error.code, api_error.message)

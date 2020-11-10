import importlib
import os
import pkgutil

from crc.api.common import ApiError


class Script(object):
    """ Provides an abstract class that defines how scripts should work, this
    must be extended in all Script Tasks."""

    def get_description(self):
        raise ApiError("invalid_script",
                       "This script does not supply a description.")

    def do_task(self, task, study_id, workflow_id, **kwargs):
        raise ApiError("invalid_script",
                       "This is an internal error. The script you are trying to execute '%s' " % self.__class__.__name__ +
                       "does not properly implement the do_task function.")

    def do_task_validate_only(self, task, study_id, workflow_id, **kwargs):
        raise ApiError("invalid_script",
                       "This is an internal error. The script you are trying to execute '%s' " % self.__class__.__name__ +
                       "does must provide a validate_only option that mimics the do_task, " +
                       "but does not make external calls or database updates." )
    @staticmethod
    def generate_augmented_list(task, study_id,workflow_id):
        """
        this makes a dictionary of lambda functions that are closed over the class instance that
        They represent. This is passed into PythonScriptParser as a list of helper functions that are
        available for running.  In general, they maintain the do_task call structure that they had, but
        they always return a value rather than updating the task data.

        We may be able to remove the task for each of these calls if we are not using it other than potentially
        updating the task data.
        """
        def make_closure(subclass,task,study_id,workflow_id):
            instance = subclass()
            return lambda *a : subclass.do_task(instance,task,study_id,workflow_id,*a)
        execlist = {}
        subclasses = Script.get_all_subclasses()
        for x in range(len(subclasses)):
            subclass = subclasses[x]
            execlist[subclass.__module__.split('.')[-1]] = make_closure(subclass,task,study_id,
                                                                                       workflow_id)
        return execlist

    @staticmethod
    def generate_augmented_validate_list(task, study_id, workflow_id):
        """
        this makes a dictionary of lambda functions that are closed over the class instance that
        They represent. This is passed into PythonScriptParser as a list of helper functions that are
        available for running.  In general, they maintain the do_task call structure that they had, but
        they always return a value rather than updating the task data.

        We may be able to remove the task for each of these calls if we are not using it other than potentially
        updating the task data.
        """

        def make_closure_validate(subclass,task,study_id,workflow_id):
            instance = subclass()
            return lambda *a : subclass.do_task_validate_only(instance,task,study_id,workflow_id,*a)
        execlist = {}
        subclasses = Script.get_all_subclasses()
        for x in range(len(subclasses)):
            subclass = subclasses[x]
            execlist[subclass.__module__.split('.')[-1]] = make_closure_validate(subclass,task,study_id,
                                                                                       workflow_id)
        return execlist




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

    def add_data_to_task(self, task, data):
        key = self.__class__.__name__
        if key in task.data:
            task.data[key].update(data)
        else:
            task.data[key] = data

class ScriptValidationError:

    def __init__(self, code, message):
        self.code = code
        self.message = message

    @classmethod
    def from_api_error(cls, api_error: ApiError):
        return cls(api_error.code, api_error.message)

class DataStoreBase():
    def overwritten(self,value,prev_value):
        if prev_value == None:
            overwritten = False
        else:
            if prev_value == value:
                overwritten = False
            else:
                overwritten = True
        return overwritten

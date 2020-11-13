import importlib
import os
import pkgutil
from crc import session
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.workflow import WorkflowModel
from datetime import datetime

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

    def set_validate_common(self, study_id, workflow_id, user_id, script_name, *args):
        self.check_args_2(args,script_name)
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        self.get_prev_value(study_id=study_id,user_id=user_id, key=args[0])

    def check_args(self, args, maxlen=1, script_name='study_data_get'):
        if len(args) < 1 or len(args) > maxlen :
            raise ApiError(code="missing_argument",

            message="The %s script takes either one or two arguments, starting with the key and an "%script_name + \
                    "optional default")

    def check_args_2(self, args, script_name='study_data_set'):
        if len(args) != 2:
            raise ApiError(code="missing_argument",
            message="The %s script takes two arguments, starting with the key and a "%script_name +\
                    "value for the key")

    def get_prev_value(self,study_id,user_id,key):
        study = session.query(DataStoreModel).filter_by(study_id=study_id,user_id=user_id,key=key).first()
        return study



    def set_data_common(self, task_id, study_id, user_id, workflow_id, workflow_spec_id, script_name, *args, **kwargs):

        self.check_args_2(args,script_name=script_name)
        study = self.get_prev_value(study_id=study_id,user_id=user_id, key=args[0])
        if workflow_spec_id is None and workflow_id is not None:
            workflow = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            workflow_spec_id = workflow.workflow_spec_id
        if study is not None:
            prev_value = study.value
        else:
            prev_value = None
            study = DataStoreModel(key=args[0],value=args[1],
                                   study_id=study_id,
                                   task_id=task_id,
                                   user_id=user_id,             # Make this available to any User
                                   workflow_id= workflow_id,
                                   spec_id=workflow_spec_id)
        study.value = args[1]
        study.last_updated = datetime.now()
        overwritten = self.overwritten(study.value,prev_value)
        session.add(study)
        session.commit()
        return {'new_value':study.value,
                'old_value':prev_value,
                'overwritten':overwritten}


    def get_data_common(self, study_id, user_id, script_name, *args):
        self.check_args(args,2,script_name)
        study = session.query(DataStoreModel).filter_by(study_id=study_id,user_id=user_id,key=args[0]).first()
        if study:
            return study.value
        else:
            return args[1]

    def get_multi_common(self, study_id, user_id):
        study = session.query(DataStoreModel).filter_by(study_id=study_id,user_id=user_id)
        return (study)


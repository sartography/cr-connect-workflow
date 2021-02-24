import re

generic_message = """Workflow validation failed. For more information about the error, see below."""

known_errors = {'Error is Non-default exclusive outgoing sequence flow  without condition':
                    {'message': 'Missing condition', 'hint': 'Add a Condition Type to your gateway path.'},
                '^Could not set task title on task (\w+) with \'(.*)\' property because \\1: Error evaluating expression \'(.*)\', "\'Box\' object has no attribute \'\\2\'"$':
                    {'hint': 'You are overriding the title for task xxx, using the display_name extension, and it is causing an error.  Look under the extensions tab for the task, and check the value you are setting for the display_name'}}


class ValidationErrorService(object):

    """Validation Error Service interprets messages return from api.workflow.validate_workflow_specification
       Validation is run twice,
       once  where we try to fill in all form fields
       and a second time where we only fill in the required fields.

       We get a list that contains possible errors from the validation."""

    @staticmethod
    def interpret_validation_errors(errors):
        if len(errors) == 0:
            return ()

        interpreted_errors = []

        for error_type in ['all', 'required']:
            if error_type in errors:
                hint = generic_message
                for known_key in known_errors:
                    if known_key in errors[error_type].message:
                        if 'hint' in known_errors[known_key]:
                            hint = known_errors[known_key]['hint']

                errors[error_type].hint = hint
                interpreted_errors.append(errors[error_type])

        return interpreted_errors

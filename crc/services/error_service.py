import re

generic_message = """Workflow validation failed. For more information about the error, see below."""

# known_errors is a dictionary of errors from validation that we want to give users a hint for solving their problem.
# The key is the known error, or part of the known error. It is a string.
# We use the key to see if we have a known error.
# The value is a dictionary that contains the hint for the user.

# If we want to capture details about the error we can use a regex for the key.
# If you use a regex, you must add a groups entry to the value dictionary.
# groups is a dictionary defining the values returned from the groups() method from  the regex search.
# They key is the string used as a placeholder in the hint, and the value is the groups index.

# I know this explanation is confusing. If you have ideas for clarification, pull request welcome.

known_errors = {'Error is Non-default exclusive outgoing sequence flow  without condition':
                {'hint': 'Add a Condition Type to your gateway path.'},

                'Could not set task title on task .*':
                {'hint': 'You are overriding the title using an extension and it is causing this error. '
                         'Look under the extensions tab for the task, and check the value you are setting '
                         'for the property.'}}


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
                    regex = re.compile(known_key)
                    result = regex.search(errors[error_type].message)
                    if result is not None:
                        if 'hint' in known_errors[known_key]:
                            if 'groups' in known_errors[known_key]:
                                caught = {}

                                for group in known_errors[known_key]['groups']:
                                    group_id = known_errors[known_key]['groups'][group]
                                    group_value = result.groups()[group_id]
                                    caught[group] = group_value

                                hint = known_errors[known_key]['hint'].format(**caught)
                            else:
                                hint = known_errors[known_key]['hint']

                errors[error_type].hint = hint
                interpreted_errors.append(errors[error_type])

        return interpreted_errors

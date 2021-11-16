import re


# known_errors is a dictionary of errors from validation that we want to give users a hint for solving their problem.
# The key is the known error, or part of the known error. It is a string.
# We use the key to see if we have a known error.
# The value is a dictionary that contains the hint for the user.

# If we want to capture details about the error we can use a regex for the key.
# If you use a regex, you must add a groups entry to the value dictionary.
# groups is a dictionary defining the values returned from the groups() method from  the regex search.
# They key is the string used as a placeholder in the hint, and the value is the groups index.

# I know this explanation is confusing. If you have ideas for clarification, pull request welcome.

known_errors = {'Non-default exclusive outgoing sequence flow  without condition':
                {'hint': 'Add a Condition Type to your gateway path.'},

                'Could not set task title on task .*':
                {'hint': 'You are overriding the title using an extension and it is causing this error. '
                         'Look under the extensions tab for the task, and check the value you are setting '
                         'for the property.'},
                'Error opening excel file .*, with file_model_id:':
                {'hint': 'It looks like you are trying to use an older xls file. '
                         'Try uploading a newer xlsx file.'}}


class ValidationErrorService(object):

    """Validation Error Service interprets messages return from api.workflow.validate_workflow_specification
       Validation is run twice,
       once  where we try to fill in all form fields
       and a second time where we only fill in the required fields.
       We get a list that contains possible errors from the validation."""

    @staticmethod
    def interpret_validation_error(error):
        if error is None:
            return
        for known_key in known_errors:
            regex = re.compile(known_key)
            result = regex.search(error.message)
            if result is not None:
                if 'hint' in known_errors[known_key]:
                    error.hint = known_errors[known_key]['hint']
        return error

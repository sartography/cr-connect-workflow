# known_errors
#   key - something we can search for in an error message.
#   both_message - human readable message return to the user if error occurs in both
#   required_message - human readable message return to the user if error only occurs in required
#   all_message -human readable message return to the user if error only occurs in all
#
# known_errors = [{'key': 'Error is Non-default exclusive outgoing sequence flow  without condition',
#                  'message': 'Missing condition', 'hint': 'Add a Condition Type to your gateway path.'}]
known_errors = {'Error is Non-default exclusive outgoing sequence flow  without condition':
                    {'message': 'Missing condition', 'hint': 'Add a Condition Type to your gateway path.'}}
generic_message = """Workflow validation failed. For more information about the error, see below."""
# error_keys = [error['key'] for error in known_errors]

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
        # hint = ''
        interpreted_errors = []

        for error_type in ['all', 'required']:
            if error_type in errors:
                hint = generic_message
                for known_key in known_errors:
                    if known_key in errors[error_type].message:
                        if 'hint' in known_errors[known_key]:
                            hint = known_errors[known_key]['hint']
                        # else:
                        #     hint = generic_message
                errors[error_type].hint = hint
                interpreted_errors.append(errors[error_type])

        # for known_error in known_errors:
        #     if known_error['key'] in errors['all'].message:
        #
        #         # in both error all and error required
        #         if known_error['key'] in errors['required'].message:
        #             if 'hint' in known_error.keys():
        #                 hint = known_error['hint']
        #             else:
        #                 hint = generic_message
        #
        #         # just in error all
        #         else:
        #             pass
        #
        #     # just in error required
        #     if known_error['key'] in errors['required'].message:
        #         pass

        return interpreted_errors

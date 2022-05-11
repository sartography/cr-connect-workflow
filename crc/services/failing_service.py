from flask_bpmn.api.api_error import ApiError


class FailingService(object):

    @staticmethod
    def fail_as_service():
        """It fails"""

        raise ApiError(code='bad_service',
                       message='This is my failing service')

class RestException(Exception):
    status_code = 400
    EXPRESSION_ERROR = {'code': 'invalid_expression', 'message': 'The expression you '}

    def __init__(self, payload, status_code=None, details=None):
        Exception.__init__(self)
        if 'status_code' in payload:
            self.status_code = payload['status_code']
        if status_code is not None:
            self.status_code = status_code
        if details is not None:
            payload['details'] = details
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload)
        return rv

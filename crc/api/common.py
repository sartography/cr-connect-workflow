from crc import ma, app


class ApiError(Exception):
    def __init__(self, code, message, status_code=400):
        self.status_code = status_code
        self.code = code
        self.message = message
        Exception.__init__(self, self.message)


class ApiErrorSchema(ma.Schema):
    class Meta:
        fields = ("code", "message")


@app.errorhandler(ApiError)
def handle_invalid_usage(error):
    response = ApiErrorSchema().dump(error)
    return response, error.status_code

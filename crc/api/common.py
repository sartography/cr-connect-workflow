from crc import ma


class ApiError:
    def __init__(self, code, message):
        self.code = code
        self.message = message


class ApiErrorSchema(ma.Schema):
    class Meta:
        fields = ("code", "message")


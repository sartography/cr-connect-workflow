import io
import json
import uuid
from io import BytesIO

import connexion
import jinja2
from docxtpl import DocxTemplate
from flask import send_file
from jinja2 import Template, UndefinedError

from crc.api.common import ApiError, ApiErrorSchema
from crc.scripts.CompleteTemplate import CompleteTemplate
from crc.services.file_service import FileService


def render_markdown(data, template):
    """
    Provides a quick way to very that a Jinja markdown template will work properly on a given json 
    data structure.  Useful for folks that are building these markdown templates.
    """
    try:
        template = Template(template)
        data = json.loads(data)
        return template.render(**data)
    except UndefinedError as ue:
        raise ApiError(code="undefined field", message=ue.message)
    except Exception as e:
        raise ApiError(code="invalid", message=str(e))


def render_docx(data):
    """
    Provides a quick way to verify that a Jinja docx template will work properly on a given json
    data structure.  Useful for folks that are building these templates.
    """
    try:
        file = connexion.request.files['file']
        target_stream = CompleteTemplate().make_template(file, json.loads(data))
        return send_file(
            io.BytesIO(target_stream.read()),
            as_attachment=True,
            attachment_filename="output.docx",
            mimetype="application/octet-stream",
            cache_timeout=-1  # Don't cache these files on the browser.
        )
    except ValueError as e:
        raise ApiError(code="invalid", message=str(e))
    except Exception as e:
        raise ApiError(code="invalid", message=str(e))

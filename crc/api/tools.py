import hashlib
import io
import json
import inspect
import os

import connexion
from SpiffWorkflow.bpmn.PythonScriptEngine import Box
from flask import send_file
from jinja2 import Template, UndefinedError

from crc import app
from flask_bpmn.api.common import ApiError
from crc.scripts.complete_template import CompleteTemplate
from crc.scripts.script import Script

from crc.services.email_service import EmailService
from config.default import DEFAULT_SENDER
from crc.services.jinja_service import JinjaService
from crc.services.workflow_processor import CustomBpmnScriptEngine


def render_markdown(data, template):
    """
    Provides a quick way to very that a Jinja markdown template will work properly on a given json
    data structure.  Useful for folks that are building these markdown templates.
    """
    try:
        data = json.loads(data)
        return JinjaService.get_content(template, data)
    except UndefinedError as ue:
        raise ApiError(code="undefined_field", message=ue.message)
    except Exception as e:
        raise ApiError(code="invalid_render", message=str(e))


def render_docx():
    """
    Provides a quick way to verify that a Jinja docx template will work properly on a given json
    data structure.  Useful for folks that are building these templates.
    """
    try:
        file = connexion.request.files['file']
        data = connexion.request.form['data']
        # TODO: This bypasses the Jinja service and uses complete_template script
        target_stream = JinjaService().make_template(file, json.loads(data))
        return send_file(
            io.BytesIO(target_stream.read()),
            as_attachment=True,
            attachment_filename="output.docx",
            mimetype="application/octet-stream",
            cache_timeout=-1  # Don't cache these files on the browser.
        )
    except ValueError as e:
        raise ApiError(code="undefined_field", message=str(e))
    except Exception as e:
        raise ApiError(code="invalid_render", message=str(e))


def list_scripts():
    """Provides a list of scripts that can be called by a script task."""
    scripts = Script.get_all_subclasses()
    script_meta = []
    for script_class in scripts:
        file_path = inspect.getfile(script_class)
        file_name = os.path.basename(file_path)
        # This grabs the filename without the suffix,
        # which is what configurators actually use in a script task.
        handle = os.path.splitext(file_name)[0]
        meta_data = {
            "name": script_class.__name__,
            "handle": handle,
            "description": script_class().get_description()
        }
        script_meta.append(meta_data)
    return script_meta


def send_email(subject, address, body, data=None):
    """Just sends a quick test email to assure the system is working."""
    if address and body:
        body = body.decode('UTF-8')
        return send_test_email(subject, address, body, json.loads(data))
    else:
        raise ApiError(code='missing_parameter',
                       message='You must provide an email address and a message.')


def evaluate_python_expression(body):
    """Evaluate the given python expression, returning its result.  This is useful if the
    front end application needs to do real-time processing on task data. If for instance
    there is a hide expression that is based on a previous value in the same form.
    The response includes both the result, and a hash of the original query, subsequent calls
    of the same hash are unnecessary. """

    # In an effort to speed things up, try evaluating the expression immediately, with just the data as
    # context,  if this failes, then run it through the full expression engine.
    try:
        eval(body['expression'], Box(body['data']))
    except Exception as e:
        app.logger.info("Failed to handle expression immediately, doing a more complex operation.")

    try:
        script_engine = CustomBpmnScriptEngine()
        result = script_engine._evaluate(body['expression'], body['data'])
        return {"result": result, "expression": body['expression'], "key": body['key']}
    except Exception as e:
        return {"result": False, "expression": body['expression'], "key": body['key'], "error": str(e)}


def send_test_email(subject, address, message, data=None):
    content, content_html = EmailService().get_rendered_content(message, data)
    EmailService.add_email(
        subject=subject,
        sender=DEFAULT_SENDER,
        recipients=[address],
        content=content,
        content_html=content_html)

import io
import json

import connexion
from SpiffWorkflow.bpmn.PythonScriptEngine import PythonScriptEngine
from flask import send_file
from jinja2 import Template, UndefinedError

from crc.api.common import ApiError
from crc.scripts.complete_template import CompleteTemplate
from crc.scripts.script import Script
import crc.scripts
from crc.services.mails import send_test_email
from crc.services.workflow_processor import WorkflowProcessor


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
        target_stream = CompleteTemplate().make_template(file, json.loads(data))
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
        script_meta.append(
            {
                "name": script_class.__name__,
                "description": script_class().get_description()
            })
    return script_meta


def send_email(address):
    """Just sends a quick test email to assure the system is working."""
    if not address:
        address = "dan@sartography.com"
    return send_test_email(address, [address])


def evaluate_python_expression(expression, body):
    """Evaluate the given python expression, returning it's result.  This is useful if the
    front end application needs to do real-time processing on task data. If for instance
    there is a hide expression that is based on a previous value in the same form."""
    try:
        # fixme: The script engine should be pulled from Workflow Processor,
        #  but the one it returns overwrites the evaluate expression making it uncallable.
        script_engine = PythonScriptEngine()
        return script_engine.evaluate(expression, **body)
    except Exception as e:
        raise ApiError("expression_error", str(e))

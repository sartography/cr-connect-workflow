from docxtpl import DocxTemplate, Listing, InlineImage
from jinja2 import Environment, DictLoader

from docx.shared import Inches
from io import BytesIO

import copy


class JinjaService:
    """Service for Jinja2 templates.

Includes the ability to embed templates inside templates, using task.data.

-- In task.data
name = "Dan"
my_template = "Hi {{name}}, This is a jinja template too!"

-- In Element Documentation
Please Introduce yourself.
{% include 'my_template' %}
Cool Right?

-- Produces
Please Introduce yourself.
Hi Dan, This is a jinja template too!
Cool Right?
"""

    @staticmethod
    def get_content(input_template, data):
        templates = data
        templates['main_template'] = input_template
        jinja2_env = Environment(loader=DictLoader(templates))

        # We just make a call here and let any errors percolate up to the calling method
        template = jinja2_env.get_template('main_template')
        return template.render(**data)


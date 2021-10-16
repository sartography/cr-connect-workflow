from jinja2 import Environment, DictLoader


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

        try:
            template = jinja2_env.get_template('main_template')

        except Exception:
            # TODO: Should we deal w/ specific exceptions here?
            # i.e., the ones in workflow_service._process_documentation
            raise

        else:
            return template.render(**data)

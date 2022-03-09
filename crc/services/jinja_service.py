import re
import sys
import traceback

from docx.shared import Inches
from docxtpl import DocxTemplate, Listing, InlineImage
from io import BytesIO
from jinja2 import Environment, DictLoader, TemplateSyntaxError

import copy

from crc.api.common import ApiError


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
    template_pattern = re.compile('{ ?% ?include\s*[\'\"](\w+)[\'\"]\s*?-?%}', re.DOTALL)

    @staticmethod
    def get_content(input_template, data):
        templates = {}
        references = JinjaService.template_references(input_template)
        for ref in references:
            if ref in data.keys():
                templates[ref] = data[ref]
            else:
                raise ApiError("missing_template", f"Your documentation imports a template that doest not exist: {ref}")
        templates['main_template'] = input_template
        jinja2_env = Environment(loader=DictLoader(templates))
        # We just make a call here and let any errors percolate up to the calling method
        template = jinja2_env.get_template('main_template')
        try:
            result = template.render(**data)
        except AttributeError as ae:
            if str(ae) == '\'NoneType\' object has no attribute \'splitlines\'':
                raise ApiError("template_error", "Error processing template.  You may be using a wordwrap "
                                                 "with a field that has no value.")

        return result


    @staticmethod
    def template_references(input_template):
        """Using regex, determine what other templates are included, and return a list of those names."""
        matches = JinjaService.template_pattern.findall(input_template)
        return matches
    #
    # The rest of this is for using Word documents as Jinja templates
    #
    def make_template(self, binary_stream, context, image_file_data=None):
        templates = context
        doc = DocxTemplate(binary_stream)
        doc_context = copy.deepcopy(context)
        doc_context = self.rich_text_update(doc_context)
        doc_context = self.append_images(doc, doc_context, image_file_data)
        jinja_env = Environment(loader=DictLoader(templates), autoescape=True)

        try:
            doc.render(doc_context, jinja_env)
        except TemplateSyntaxError as tse:
            line_number = tse.lineno

            # the doc renderer code is trying to give context, returning 3 lines
            # before and after the error if possible.  The can result in a lot of
            # garbage, too much to send back.  Sometimes the line itself is too large.
            # Just trying to get something sensible if possible.
            context = list(tse.docx_context)
            if len(context) == 1: # It just sent us the whole damn thing back.  Useless.
                error_line = "Unable to determine location of error in the word document. Opening and Saving the " \
                             "template in LibreOffice may fix this problem."
            elif len(context) == 7:
                error_line = context[3]
            else:
                error_line = ", ".join(context)

            # If the bloodly thing is still stupid long, try grabbing the middle 200
            # characters.
            if len(error_line) > 500:
                offset = int(len(error_line)/2 - 100)
                error_line = "Error occurred near:  " + error_line[offset: -offset]

            raise ApiError(code="template_error", message="Word Document creation error : %s" % str(tse),
                           line_number=line_number, error_line=error_line)
        target_stream = BytesIO()
        doc.save(target_stream)
        target_stream.seek(0)  # move to the beginning of the stream.
        return target_stream

    def rich_text_update(self, context):
        """This is a bit of a hack.  If we find that /n characters exist in the data, we want
        these to come out in the final document without requiring someone to predict it in the
        template.  Ideally we would use the 'RichText' feature of the python-docx library, but
        that requires we both escape it here, and in the Docx template.  There is a thing called
        a 'listing' in python-docx library that only requires we use it on the way in, and the
        template doesn't have to think about it.  So running with that for now."""
        # loop through the content, identify anything that has a newline character in it, and
        # wrap that sucker in a 'listing' function.
        if isinstance(context, dict):
            for k, v in context.items():
                context[k] = self.rich_text_update(v)
        elif isinstance(context, list):
            for i in range(len(context)):
                context[i] = self.rich_text_update(context[i])
        elif isinstance(context, str) and '\n' in context:
            return Listing(context)
        return context

    def append_images(self, template, context, image_file_data):
        context['images'] = {}
        if image_file_data is not None:
            for file_data_model in image_file_data:
                fm = file_data_model.file_model
                if fm is not None:
                    context['images'][fm.id] = {
                        'name': fm.name,
                        'url': '/v1.0/file/%s/data' % fm.id,
                        'image': self.make_image(file_data_model, template)
                    }

        return context

    @staticmethod
    def make_image(file_data_model, template):
        return InlineImage(template, BytesIO(file_data_model.data), width=Inches(6.5))

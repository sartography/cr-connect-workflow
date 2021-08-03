from crc.models.workflow import WorkflowSpecModel
from crc.scripts.script import Script
from crc.services.file_service import FileService
from crc import app, session

from lxml import etree
from io import StringIO, BytesIO

import pandas as pd
import os
import random
import string


class DMNFromSpreadSheet(Script):

    def _get_random_string(self, length):
        return ''.join(
            [random.choice(string.ascii_letters + string.digits) for n in range(length)])


    def _row_has_value(self, values):
        for item in values:
            if not pd.isnull(item):
                return True
        return False

    def get_description(self):
        """Create a DMN table from a spreadsheet"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        pass

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        # ss_file_path = os.path.join(app.root_path, 'static', 'spreadsheet_to_dmn.xlsx')
        # ss_file_path = os.path.join(app.root_path, 'static', 'New_test_budget_spreadsheet.xlsx')
        ss_file_path = os.path.join(app.root_path, 'static', 'large_test_spreadsheet.xlsx')
        df = pd.read_excel(ss_file_path, header=None)

        root = etree.Element("definitions",
                             xmlns="http://www.omg.org/spec/DMN/20151101/dmn.xsd",
                             id='Definitions',
                             name="DRD",
                             namespace="http://camunda.org/schema/1.0/dmn")
        decision_name = df.iat[0, 1]
        decision_id = df.iat[1, 1]
        decision = etree.SubElement(root, "decision",
                                    id=decision_id,
                                    name=decision_name
                                    )
        decision_table = etree.SubElement(decision, 'decisionTable', id='decisionTable_1')
        input_output = df.iloc[2][1:]
        count = 1
        input_count = 1
        output_count = 1
        for item in input_output:
            if item == 'Input':
                label = df.iloc[3, count]
                input_ = etree.SubElement(decision_table, 'input', id=f'input_{input_count}', label=label)
                type_ref = df.iloc[5, count]
                input_expression = etree.SubElement(input_, 'inputExpression', id=f'inputExpression_{input_count}',
                                                    typeRef=type_ref)
                expression = df.iloc[4, count]
                expression_text = etree.SubElement(input_expression, 'text')
                expression_text.text = expression

                input_count += 1
            elif item == 'Output':
                label = df.iloc[3, count]
                name = df.iloc[4, count]
                type_ref =df.iloc[5, count]
                decision_table.append(etree.Element('output', id=f'output_{output_count}',
                                                    label=label, name=name, typeRef=type_ref))
                output_count += 1
            elif item == 'Annotation':
                column_count = count
                break
            count += 1

        row = 6
        while row < df.shape[0]:
            column = 1
            row_values = df.iloc[row].values[1:column_count]
            if self._row_has_value(row_values):
                rando = self._get_random_string(7).lower()
                rule = etree.SubElement(decision_table, 'rule', id=f'DecisionRule_{rando}')

                i = 1
                while i < input_count:
                    input_entry = etree.SubElement(rule, 'inputEntry', id=f'UnaryTests_{self._get_random_string(7)}')
                    text_element = etree.SubElement(input_entry, 'text')
                    text_element.text = str(df.iloc[row, column]) if not pd.isnull(df.iloc[row, column]) else ''
                    i += 1
                    column += 1
                i = 1
                while i < output_count:
                    output_entry = etree.SubElement(rule, 'outputEntry', id=f'LiteralExpression_{self._get_random_string(7)}')
                    text_element = etree.SubElement(output_entry, 'text')
                    text_element.text = str(df.iloc[row, column]) if not pd.isnull(df.iloc[row, column]) else ''
                    i += 1
                    column += 1

                description = etree.SubElement(rule, 'description')
                text = df.iloc[row, column] if not pd.isnull(df.iloc[row, column]) else ''
                description.text = text

            row += 1

        filename = 'test_dmn.dmn'
        primary = False
        content_type = 'text/xml'

        prefix = b'<?xml version="1.0" encoding="UTF-8"?>'
        file_data = prefix + etree.tostring(root)
        data = {'file': (BytesIO(file_data), filename)}
        file = BytesIO(file_data)

        workflow_spec = session.query(WorkflowSpecModel).first()
        file_model = FileService.add_workflow_spec_file(workflow_spec, filename, content_type,
                                                        file.read(), primary=primary)


        print('dmn from spreadsheet')

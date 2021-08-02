from crc.scripts.script import Script
from crc import app

from lxml import etree
from io import StringIO, BytesIO

import pandas as pd
import os


class DMNFromSpreadSheet(Script):

    def get_description(self):
        """Create a DMN table from a spreadsheet"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        pass

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        # dmn_template_path = os.path.join(app.root_path, 'static', 'templates', 'dmn_template.xml')
        dmn_template_path = os.path.join(app.root_path, 'static', 'templates', 'diagram_1.dmn')
        ss_file_path = os.path.join(app.root_path, 'static', 'spreadsheet_to_dmn.xlsx')
        f_open = open(dmn_template_path, 'r')
        xml_template = f_open.read()
        tree = etree.parse(StringIO(xml_template))
        df = pd.read_excel(ss_file_path, header=None)
        decision_name = df.iat[0, 1]
        decision_id = df.iat[1, 1]
        input_output = df.iloc[2][1:]
        for index, item in input_output:
            if item == 'Input':
                print('input')
            if item == 'Output':
                print('output')

        print(df)

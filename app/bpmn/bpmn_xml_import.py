import os

from pm4pybpmn.objects.bpmn.importer import bpmn20 as bpmn_importer
from pm4pybpmn.visualization.bpmn.util.bpmn_to_figure import bpmn_diagram_to_figure


class BpmnXmlImport(object):
    def __init__(self):
        pass

    @staticmethod
    def bpmn_xml_to_graph(file_path="app/static/diagram.bpmn"):
        return bpmn_importer.import_bpmn(os.path.normpath(file_path))

    @staticmethod
    def graph_to_figure(bpmn_graph):
        return bpmn_diagram_to_figure(bpmn_graph=bpmn_graph, image_format='png')

import json

from django.core import serializers
from django.views.generic.base import TemplateView

from app.bpmn.bpmn_xml_import import BpmnXmlImport


class BpmnXmlImportView(TemplateView):
    template_name = "load_bpmn.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bpmn_graph = BpmnXmlImport.bpmn_xml_to_graph()
        context['bpmn_graph'] = bpmn_graph
        context['bpmn_fig'] = BpmnXmlImport.graph_to_figure(bpmn_graph)
        return context

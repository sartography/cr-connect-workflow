from tests.base_test import BaseTest

from crc import session
from crc.models.file import FileModel, FileDataModel, LookupFileModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecDependencyFile
from crc.services.file_service import FileService

from sqlalchemy import desc

import io
import json


class TestFileDataCleanup(BaseTest):

    xml_str_one = b"""<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" id="Definitions_0e68fp5" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Modeler" exporterVersion="3.0.0-dev">
      <bpmn:process id="Process_054hyyv" isExecutable="true">
        <bpmn:startEvent id="StartEvent_1" />
      </bpmn:process>
      <bpmndi:BPMNDiagram id="BPMNDiagram_1">
        <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_054hyyv">
          <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
            <dc:Bounds x="179" y="159" width="36" height="36" />
          </bpmndi:BPMNShape>
        </bpmndi:BPMNPlane>
      </bpmndi:BPMNDiagram>
    </bpmn:definitions>"""

    xml_str_two = b"""<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_0e68fp5" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Modeler" exporterVersion="4.2.0">
      <bpmn:process id="Process_054hyyv" isExecutable="true">
        <bpmn:startEvent id="StartEvent_1">
          <bpmn:outgoing>Flow_1v0s5ht</bpmn:outgoing>
        </bpmn:startEvent>
        <bpmn:task id="Activity_08xcoa5" name="Say Hello">
          <bpmn:documentation># Hello</bpmn:documentation>
          <bpmn:incoming>Flow_1v0s5ht</bpmn:incoming>
          <bpmn:outgoing>Flow_12k5ua1</bpmn:outgoing>
        </bpmn:task>
        <bpmn:sequenceFlow id="Flow_1v0s5ht" sourceRef="StartEvent_1" targetRef="Activity_08xcoa5" />
        <bpmn:endEvent id="Event_10ufcgd">
          <bpmn:incoming>Flow_12k5ua1</bpmn:incoming>
        </bpmn:endEvent>
        <bpmn:sequenceFlow id="Flow_12k5ua1" sourceRef="Activity_08xcoa5" targetRef="Event_10ufcgd" />
      </bpmn:process>
      <bpmndi:BPMNDiagram id="BPMNDiagram_1">
        <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_054hyyv">
          <bpmndi:BPMNEdge id="Flow_1v0s5ht_di" bpmnElement="Flow_1v0s5ht">
            <di:waypoint x="215" y="117" />
            <di:waypoint x="270" y="117" />
          </bpmndi:BPMNEdge>
          <bpmndi:BPMNEdge id="Flow_12k5ua1_di" bpmnElement="Flow_12k5ua1">
            <di:waypoint x="370" y="117" />
            <di:waypoint x="432" y="117" />
          </bpmndi:BPMNEdge>
          <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
            <dc:Bounds x="179" y="99" width="36" height="36" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNShape id="Activity_08xcoa5_di" bpmnElement="Activity_08xcoa5">
            <dc:Bounds x="270" y="77" width="100" height="80" />
          </bpmndi:BPMNShape>
          <bpmndi:BPMNShape id="Event_10ufcgd_di" bpmnElement="Event_10ufcgd">
            <dc:Bounds x="432" y="99" width="36" height="36" />
          </bpmndi:BPMNShape>
        </bpmndi:BPMNPlane>
      </bpmndi:BPMNDiagram>
    </bpmn:definitions>
    """

    def test_file_data_cleanup(self):
        """Update a file twice. Make sure we clean up the correct files"""

        self.load_example_data()
        workflow = self.create_workflow('empty_workflow')
        file_data_model_count = session.query(FileDataModel).count()

        # Use for comparison after cleanup
        replaced_models = []

        # Get `empty_workflow` workflow spec
        workflow_spec_model = session.query(WorkflowSpecModel)\
            .filter(WorkflowSpecModel.id == 'empty_workflow')\
            .first()

        # Get file model for empty_workflow spec
        file_model = session.query(FileModel)\
            .filter(FileModel.workflow_spec_id == workflow_spec_model.id)\
            .first()

        # Grab the file data model for empty_workflow file_model
        original_file_data_model = session.query(FileDataModel)\
            .filter(FileDataModel.file_model_id == file_model.id)\
            .order_by(desc(FileDataModel.date_created))\
            .first()

        # Add file to dependencies
        # It should not get deleted
        wf_spec_depend_model = WorkflowSpecDependencyFile(file_data_id=original_file_data_model.id,
                                                          workflow_id=workflow.id)
        session.add(wf_spec_depend_model)
        session.commit()

        # Update first time
        replaced_models.append(original_file_data_model)
        data = {'file': (io.BytesIO(self.xml_str_one), file_model.name)}
        rv = self.app.put('/v1.0/file/%i/data' % file_model.id, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_json_first = json.loads(rv.get_data(as_text=True))

        # Update second time
        # replaced_models.append(old_file_data_model)
        data = {'file': (io.BytesIO(self.xml_str_two), file_model.name)}
        rv = self.app.put('/v1.0/file/%i/data' % file_model.id, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_json_second = json.loads(rv.get_data(as_text=True))

        # Add lookup file
        data = {'file': (io.BytesIO(b'asdf'), 'lookup_1.xlsx')}
        rv = self.app.post('/v1.0/file?workflow_spec_id=%s' % workflow_spec_model.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_json = json.loads(rv.get_data(as_text=True))
        lookup_file_id = file_json['id']
        lookup_data_model = session.query(FileDataModel).filter(FileDataModel.file_model_id == lookup_file_id).first()
        lookup_model = LookupFileModel(file_data_model_id=lookup_data_model.id,
                                       workflow_spec_id=workflow_spec_model.id)
        session.add(lookup_model)
        session.commit()

        # Update lookup file
        data = {'file': (io.BytesIO(b'1234'), 'lookup_1.xlsx')}
        rv = self.app.put('/v1.0/file/%i/data' % lookup_file_id, data=data, follow_redirects=True,
                          content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)

        # Run the cleanup files process
        current_models, saved_models, deleted_models = FileService.cleanup_file_data()

        # assert correct versions are removed
        new_count = session.query(FileDataModel).count()
        self.assertEqual(8, new_count)
        self.assertEqual(4, len(current_models))
        self.assertEqual(2, len(saved_models))
        self.assertEqual(1, len(deleted_models))

        print('test_file_data_cleanup')

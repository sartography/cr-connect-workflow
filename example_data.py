import datetime
import glob
import os
import xml.etree.ElementTree as ElementTree

from crc import app, db, session
from crc.models.file import FileType, FileModel, FileDataModel
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowSpecModel
from crc.services.workflow_processor import WorkflowProcessor
from models.protocol_builder import ProtocolBuilderStatus


class ExampleDataLoader:
    def make_data(self):
        users = [
            UserModel(
                uid='dhf8r',
                email_address='dhf8r@virginia.EDU',
                display_name='Daniel Harold Funk',
                affiliation='staff@virginia.edu;member@virginia.edu',
                eppn='dhf8r@virginia.edu',
                first_name='Daniel',
                last_name='Funk',
                title='SOFTWARE ENGINEER V'
            )
        ]

        studies = [
            StudyModel(
                id=1,
                title='The impact of fried pickles on beer consumption in bipedal software developers.',
                last_updated=datetime.datetime.now(),
                protocol_builder_status=ProtocolBuilderStatus.IN_PROCESS.name,
                primary_investigator_id='dhf8r',
                sponsor='Sartography Pharmaceuticals',
                ind_number='1234',
                user_uid='dhf8r'
            ),
            StudyModel(
                id=2,
                title='Requirement of hippocampal neurogenesis for the behavioral effects of soft pretzels',
                last_updated=datetime.datetime.now(),
                protocol_builder_status=ProtocolBuilderStatus.IN_PROCESS.name,
                primary_investigator_id='dhf8r',
                sponsor='Makerspace & Co.',
                ind_number='5678',
                user_uid='dhf8r'
            ),
        ]

        workflow_specifications = \
            self.create_spec(id="crc2_training_session_enter_core_info",
                             name="crc2_training_session_enter_core_info",
                             display_name="CR Connect2 - Training Session - Core Info",
                             description='Part of Milestone 3 Deliverable')
        workflow_specifications += \
            self.create_spec(id="crc2_training_session_data_security_plan",
                             name="crc2_training_session_data_security_plan",
                             display_name="CR Connect2 - Training Session - Data Security Plan",
                             description='Part of Milestone 3 Deliverable')
        workflow_specifications += \
            self.create_spec(id="sponsor_funding_source",
                             name="sponsor_funding_source",
                             display_name="Sponsor and/or Funding Source ",
                             description='TBD')
        # workflow_specifications += \
        # self.create_spec(id="m2_demo",
        #                  name="m2_demo",
        #                  display_name="Milestone 2 Demo",
        #                  description='A simplified CR Connect workflow for demonstration purposes.')
        # workflow_specifications += \
        #     self.create_spec(id="crc_study_workflow",
        #                      name="crc_study_workflow",
        #                      display_name="CR Connect Study Workflow",
        #                      description='Draft workflow for CR Connect studies.')
        all_data = users + studies + workflow_specifications
        return all_data

    def create_spec(self, id, name, display_name="", description="", filepath=None):
        """Assumes that a directory exists in static/bpmn with the same name as the given id.
           further assumes that the [id].bpmn is the primary file for the workflow.
           returns an array of data models to be added to the database."""
        models = []
        spec = WorkflowSpecModel(id=id,
                                 name=name,
                                 display_name=display_name,
                                 description=description)
        models.append(spec)
        if not filepath:
            filepath = os.path.join(app.root_path, 'static', 'bpmn', id, "*")
        files = glob.glob(filepath)
        for file_path in files:
            noise, file_extension = os.path.splitext(file_path)
            filename = os.path.basename(file_path)
            if file_extension.lower() == '.bpmn':
                type = FileType.bpmn
            elif file_extension.lower() == '.dmn':
                type = FileType.dmn
            elif file_extension.lower() == '.svg':
                type = FileType.svg
            elif file_extension.lower() == '.docx':
                type = FileType.docx
            else:
                raise Exception("Unsupported file type:" + file_path)
                continue

            is_primary = filename.lower() == id + ".bpmn"
            file_model = FileModel(name=filename, type=type, content_type='text/xml', version="1",
                                   last_updated=datetime.datetime.now(), primary=is_primary,
                                   workflow_spec_id=id)
            models.append(file_model)
            try:
                file = open(file_path, "rb")
                data = file.read()
                if (is_primary):
                    bpmn: ElementTree.Element = ElementTree.fromstring(data)
                    spec.primary_process_id = WorkflowProcessor.get_process_id(bpmn)
                    print("Locating Process Id for " + filename + "  " + spec.primary_process_id)
                models.append(FileDataModel(data=data, file_model=file_model))
            finally:
                file.close()
        return models

    @staticmethod
    def clean_db():
        session.flush()  # Clear out any transactions before deleting it all to avoid spurious errors.
        for table in reversed(db.metadata.sorted_tables):
            session.execute(table.delete())
        session.flush()

    def load_all(self):
        for data in self.make_data():
            session.add(data)
            session.commit()
        session.flush()

import datetime
import glob
import os
import xml.etree.ElementTree as ElementTree

from crc import app, db, session
from crc.models.file import FileType, FileModel, FileDataModel, CONTENT_TYPES
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowSpecModel
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor
from crc.models.protocol_builder import ProtocolBuilderStatus


class ExampleDataLoader:
    @staticmethod
    def clean_db():
        session.flush()  # Clear out any transactions before deleting it all to avoid spurious errors.
        for table in reversed(db.metadata.sorted_tables):
            session.execute(table.delete())
        session.flush()

    def load_all(self):

        self.load_reference_documents()

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
        db.session.add_all(users)
        db.session.commit()

        studies = [
            StudyModel(
                id=1,
                title='The impact of fried pickles on beer consumption in bipedal software developers.',
                last_updated=datetime.datetime.now(),
                protocol_builder_status=ProtocolBuilderStatus.IN_PROCESS,
                primary_investigator_id='dhf8r',
                sponsor='Sartography Pharmaceuticals',
                ind_number='1234',
                user_uid='dhf8r'
            ),
            StudyModel(
                id=2,
                title='Requirement of hippocampal neurogenesis for the behavioral effects of soft pretzels',
                last_updated=datetime.datetime.now(),
                protocol_builder_status=ProtocolBuilderStatus.IN_PROCESS,
                primary_investigator_id='dhf8r',
                sponsor='Makerspace & Co.',
                ind_number='5678',
                user_uid='dhf8r'
            ),
        ]
        db.session.add_all(studies)
        db.session.commit()

        self.create_spec(id="core_info",
                         name="core_info",
                         display_name="core_info",
                         description="core_info")
        self.create_spec(id="data_security_plan",
                         name="data_security_plan",
                         display_name="data_security_plan",
                         description="data_security_plan")
        self.create_spec(id="finance",
                         name="finance",
                         display_name="finance",
                         description="finance")
        self.create_spec(id="ids",
                         name="ids",
                         display_name="ids",
                         description="ids")
        self.create_spec(id="irb_api_details",
                         name="irb_api_details",
                         display_name="irb_api_details",
                         description="irb_api_details")
        self.create_spec(id="irb_api_personnel",
                         name="irb_api_personnel",
                         display_name="irb_api_personnel",
                         description="irb_api_personnel")
        self.create_spec(id="irb_api_required_docs",
                         name="irb_api_required_docs",
                         display_name="irb_api_required_docs",
                         description="irb_api_required_docs")
        self.create_spec(id="sponsor_funding_source",
                         name="sponsor_funding_source",
                         display_name="sponsor_funding_source",
                         description="sponsor_funding_source")


    def create_spec(self, id, name, display_name="", description="", filepath=None, master_spec=False):
        """Assumes that a directory exists in static/bpmn with the same name as the given id.
           further assumes that the [id].bpmn is the primary file for the workflow.
           returns an array of data models to be added to the database."""
        global file
        file_service = FileService()
        spec = WorkflowSpecModel(id=id,
                                 name=name,
                                 display_name=display_name,
                                 description=description,
                                 is_master_spec=master_spec)
        db.session.add(spec)
        db.session.commit()
        if not filepath:
            filepath = os.path.join(app.root_path, 'static', 'bpmn', id, "*")
        files = glob.glob(filepath)
        for file_path in files:
            noise, file_extension = os.path.splitext(file_path)
            filename = os.path.basename(file_path)

            is_status = filename.lower() == 'status.bpmn'
            is_primary = filename.lower() == id + '.bpmn'
            try:
                file = open(file_path, 'rb')
                data = file.read()
                content_type = CONTENT_TYPES[file_extension[1:]]
                file_service.add_workflow_spec_file(workflow_spec=spec, name=filename, content_type=content_type,
                                                    binary_data=data, primary=is_primary, is_status=is_status)
            except IsADirectoryError as de:
                # Ignore sub directories
                pass
            finally:
                if file:
                    file.close()
        return spec

    def load_reference_documents(self):
        file_path = os.path.join(app.root_path, 'static', 'reference', 'irb_documents.xlsx')
        file = open(file_path, "rb")
        FileService.add_reference_file(FileService.IRB_PRO_CATEGORIES_FILE,
                                       binary_data=file.read(),
                                       content_type=CONTENT_TYPES['xls'])
        file.close()

import datetime
import glob
import os
import xml.etree.ElementTree as ElementTree

from crc import app, db, session
from crc.models.file import FileType, FileModel, FileDataModel, CONTENT_TYPES
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecCategoryModel
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

        categories = [
            WorkflowSpecCategoryModel(
                id=0,
                name='irb_review',
                display_name='Pass IRB Review',
                display_order=0
            ),
            WorkflowSpecCategoryModel(
                id=1,
                name='core_info',
                display_name='Core Info',
                display_order=1
            ),
            WorkflowSpecCategoryModel(
                id=2,
                name='approvals',
                display_name='Approvals',
                display_order=2
            ),
            WorkflowSpecCategoryModel(
                id=3,
                name='data_security_plan',
                display_name='Data Security Plan',
                display_order=3
            ),
            WorkflowSpecCategoryModel(
                id=4,
                name='finance',
                display_name='Finance',
                display_order=4
            ),
            WorkflowSpecCategoryModel(
                id=5,
                name='notifications',
                display_name='Notifications',
                display_order=5
            ),
        ]
        db.session.add_all(categories)
        db.session.commit()

        # Pass IRB Review
        self.create_spec(id="irb_api_personnel",
                         name="irb_api_personnel",
                         display_name="IRB API Personnel",
                         description="TBD",
                         category_id=0,
                         display_order=0)
        self.create_spec(id="irb_api_details",
                         name="irb_api_details",
                         display_name="Protocol Builder Data",
                         description="TBD",
                         category_id=0,
                         display_order=1)
        self.create_spec(id="documents_approvals",
                         name="documents_approvals",
                         display_name="Documents & Approvals",
                         description="TBD",
                         category_id=0,
                         display_order=2)

        # Core Info
        self.create_spec(id="core_info",
                         name="core_info",
                         display_name="Core Info",
                         description="TBD",
                         category_id=1,
                         display_order=0)
        self.create_spec(id="core_info_approvals_ids",
                         name="core_info_approvals_ids",
                         display_name="Core Info - Approvals - IDS",
                         description="TBD",
                         category_id=1,
                         display_order=1)
        self.create_spec(id="core_info_data_security_plan_outside",
                         name="core_info_data_security_plan_outside",
                         display_name="Core Info - Data Security Plan - Outside",
                         description="TBD",
                         category_id=1,
                         display_order=2)

        # Approvals
        self.create_spec(id="ids_full_submission",
                         name="ids_full_submission",
                         display_name="Investigative Drug Services (IDS) Full Submission",
                         description="TBD",
                         category_id=2,
                         display_order=0)
        self.create_spec(id="ids_waiver",
                         name="ids_waiver",
                         display_name="Investigational Drug Service (IDS) Waiver",
                         description="TBD",
                         category_id=2,
                         display_order=1)

        # Data Security Plan
        self.create_spec(id="data_security_plan_inside",
                         name="data_security_plan_inside",
                         display_name="Data Security Plan - Inside",
                         description="TBD",
                         category_id=3,
                         display_order=0)
        self.create_spec(id="data_security_plan_outside",
                         name="data_security_plan_outside",
                         display_name="Data Security Plan - Outside",
                         description="TBD",
                         category_id=3,
                         display_order=1)
        self.create_spec(id="data_security_plan_generate",
                         name="data_security_plan_generate",
                         display_name="Data Security Plan - Generate",
                         description="TBD",
                         category_id=3,
                         display_order=2)

        # Finance
        self.create_spec(id="sponsor_funding_source",
                         name="sponsor_funding_source",
                         display_name="Sponsor Funding Source",
                         description="TBD",
                         category_id=4,
                         display_order=0)
        self.create_spec(id="finance",
                         name="finance",
                         display_name="Finance Data",
                         description="TBD",
                         category_id=4,
                         display_order=1)

        # Notifications
        self.create_spec(id="notifications",
                         name="notifications",
                         display_name="Notifications",
                         description="TBD",
                         category_id=5,
                         display_order=0)

        # Top Level (Master Status) Workflow
        self.create_spec(id="top_level_workflow",
                         name="top_level_workflow",
                         display_name="Top Level Workflow",
                         description="Determines the status of other workflows in a study",
                         category_id=None,
                         master_spec=True)


    def create_spec(self, id, name, display_name="", description="", filepath=None, master_spec=False, category_id=None, display_order=None):
        """Assumes that a directory exists in static/bpmn with the same name as the given id.
           further assumes that the [id].bpmn is the primary file for the workflow.
           returns an array of data models to be added to the database."""
        global file
        file_service = FileService()
        spec = WorkflowSpecModel(id=id,
                                 name=name,
                                 display_name=display_name,
                                 description=description,
                                 is_master_spec=master_spec,
                                 category_id=category_id,
                                 display_order=display_order)
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

import glob
import os

from crc import app, db, session
from crc.models.file import CONTENT_TYPES
from crc.models.ldap import LdapModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecCategoryModel
from crc.services.document_service import DocumentService
from crc.services.reference_file_service import ReferenceFileService
from crc.services.spec_file_service import SpecFileService
from crc.services.study_service import StudyService
from crc.services.user_file_service import UserFileService


class ExampleDataLoader:
    @staticmethod
    def clean_db():
        session.flush()  # Clear out any transactions before deleting it all to avoid spurious errors.
        engine = session.bind.engine
        connection = engine.connect()
        for table in reversed(db.metadata.sorted_tables):
            if engine.dialect.has_table(connection, table):
                session.execute(table.delete())
        session.commit()
        session.flush()

    def load_all(self):

        self.load_reference_documents()
        categories = [
            WorkflowSpecCategoryModel(
                id=0,
                display_name='From PB',
                display_order=0
            ),
            WorkflowSpecCategoryModel(
                id=1,
                display_name='Core Info',
                display_order=1
            ),
            WorkflowSpecCategoryModel(
                id=2,
                display_name='Approvals',
                display_order=2
            ),
            WorkflowSpecCategoryModel(
                id=3,
                display_name='Data Security Plan',
                display_order=3
            ),
            WorkflowSpecCategoryModel(
                id=4,
                display_name='Finance',
                display_order=4
            ),
            WorkflowSpecCategoryModel(
                id=5,
                display_name='Notifications',
                display_order=5
            ),
            WorkflowSpecCategoryModel(
                id=6,
                display_name='Status',
                display_order=6
            ),
        ]
        db.session.execute("select setval('workflow_spec_category_id_seq',7);")
        db.session.add_all(categories)
        db.session.commit()

        # Pass IRB Review
        self.create_spec(id="irb_api_personnel",
                         display_name="Personnel",
                         description="TBD",
                         category_id=0,
                         display_order=0)
        self.create_spec(id="irb_api_details",
                         display_name="Protocol Builder Data",
                         description="TBD",
                         category_id=0,
                         display_order=1)
        self.create_spec(id="documents_approvals",
                         display_name="Documents & Approvals",
                         description="Status of all approvals and documents required from Protocol Builder",
                         category_id=0,
                         display_order=2)
        self.create_spec(id="ide_supplement",
                         display_name="IDE Supplement Info",
                         description="Supplemental information for the IDE number entered in Protocol Builder",
                         category_id=0,
                         display_order=3)
        self.create_spec(id="ind_update",
                         display_name="IND Supplement Info",
                         description="Supplement information for the Investigational New Drug(s) specified in Protocol Builder",
                         category_id=0,
                         display_order=4)

        # Core Info
        self.create_spec(id="protocol",
                         display_name="Protocol",
                         description="Upload the Study Protocol here.",
                         category_id=1,
                         display_order=0)
        self.create_spec(id="non_uva_approval",
                         display_name="Non-UVA Institutional Approval",
                         description="TBD",
                         category_id=1,
                         display_order=1)
        self.create_spec(id="core_info",
                         display_name="Core Info",
                         description="TBD",
                         category_id=1,
                         display_order=2)

        # Approvals
        self.create_spec(id="ids_full_submission",
                         display_name="Investigational Drug Service (IDS) Full Submission",
                         description="TBD",
                         category_id=2,
                         display_order=0)
        self.create_spec(id="ids_waiver",
                         display_name="Investigational Drug Service (IDS) Waiver",
                         description="TBD",
                         category_id=2,
                         display_order=1)
        self.create_spec(id="rsc_hire_submission",
                         display_name="RSC/HIRE Submission",
                         description="TBD",
                         category_id=2,
                         display_order=2)
        self.create_spec(id="rsc_hire_committee",
                         display_name="RSC/HIRE Committee",
                         description="TBD",
                         category_id=2,
                         display_order=3)
        self.create_spec(id="department_chair_approval",
                         display_name="Department Chair Approval",
                         description="TBD",
                         category_id=2,
                         display_order=4)

        # Data Security Plan
        self.create_spec(id="data_security_plan",
                         display_name="Data Security Plan",
                         description="Create and generate Data Security Plan",
                         category_id=3,
                         display_order=0)

        # Finance
        self.create_spec(id="sponsor_funding_source",
                         display_name="Sponsor Funding Source",
                         description="TBD",
                         category_id=4,
                         display_order=0)
        self.create_spec(id="finance",
                         display_name="Finance Data",
                         description="TBD",
                         category_id=4,
                         display_order=1)

        # Notifications
        self.create_spec(id="notifications",
                         display_name="Notifications",
                         description="TBD",
                         category_id=5,
                         display_order=0)

        # Status
        self.create_spec(id="enrollment_date",
                         display_name="Enrollment Date",
                         description="Study enrollment date",
                         category_id=6,
                         display_order=0)
        self.create_spec(id="abandoned",
                         display_name="Abandoned",
                         description="Place study into Abandoned status",
                         category_id=6,
                         display_order=1)

        # Top Level (Master Status) Workflow
        self.create_spec(id="top_level_workflow",
                         display_name="Top Level Workflow",
                         description="Determines the status of other workflows in a study",
                         category_id=None,
                         master_spec=True)

    def load_rrt(self):
        file_path = os.path.join(app.root_path, 'static', 'reference', 'rrt_documents.xlsx')
        file = open(file_path, "rb")
        ReferenceFileService.add_reference_file(UserFileService.DOCUMENT_LIST,
                                                binary_data=file.read(),
                                                content_type=CONTENT_TYPES['xls'])
        file.close()

        category = WorkflowSpecCategoryModel(
            id=0,
            display_name='Research Ramp-up Category',
            display_order=0
        )
        db.session.add(category)
        db.session.commit()

        self.create_spec(id="rrt_top_level_workflow",
                         display_name="Top Level Workflow",
                         description="Does nothing, we don't use the master workflow here.",
                         category_id=None,
                         master_spec=True)

        self.create_spec(id="research_rampup",
                         display_name="Research Ramp-up Toolkit",
                         description="Process for creating a new research ramp-up request.",
                         category_id=0,
                         master_spec=False)

    def load_test_data(self):
        self.load_reference_documents()

        category = WorkflowSpecCategoryModel(
            id=0,
            display_name='Test Category',
            display_order=0,
            admin=False
        )
        db.session.add(category)
        db.session.commit()

        self.create_spec(id="empty_workflow",
                         display_name="Top Level Workflow",
                         description="Does nothing, we don't use the master workflow here.",
                         category_id=None,
                         master_spec=True,
                         from_tests = True)

        self.create_spec(id="random_fact",
                         display_name="Random Fact",
                         description="The workflow for a Random Fact.",
                         category_id=0,
                         display_order=0,
                         master_spec=False,
                         from_tests=True)

    def create_spec(self, id, display_name="", description="", filepath=None, master_spec=False,
                    category_id=None, display_order=None, from_tests=False, standalone=False, library=False):
        """Assumes that a directory exists in static/bpmn with the same name as the given id.
           further assumes that the [id].bpmn is the primary file for the workflow.
           returns an array of data models to be added to the database."""
        global file
        spec = WorkflowSpecModel(id=id,
                                 display_name=display_name,
                                 description=description,
                                 is_master_spec=master_spec,
                                 category_id=category_id,
                                 display_order=display_order,
                                 standalone=standalone,
                                 library=library)
        db.session.add(spec)
        db.session.commit()
        if not filepath and not from_tests:
            filepath = os.path.join(app.root_path, 'static', 'bpmn', id, "*.*")
        if not filepath and from_tests:
            filepath = os.path.join(app.root_path, '..', 'tests', 'data', id, "*.*")

        files = glob.glob(filepath)
        for file_path in files:
            if os.path.isdir(file_path):
                continue # Don't try to process sub directories

            noise, file_extension = os.path.splitext(file_path)
            filename = os.path.basename(file_path)
            is_primary = filename.lower() == id + '.bpmn'
            file = None
            try:
                file = open(file_path, 'rb')
                data = file.read()
                content_type = CONTENT_TYPES[file_extension[1:]]
                SpecFileService.add_file(workflow_spec=spec, file_name=filename, binary_data=data)
                if is_primary:
                    SpecFileService.set_primary_bpmn(spec, filename)
            except IsADirectoryError as de:
                # Ignore sub directories
                pass
            finally:
                if file:
                    file.close()
        return spec

    def load_reference_documents(self):
        file_path = os.path.join(app.root_path, 'static', 'reference', 'documents.xlsx')
        file = open(file_path, "rb")
        ReferenceFileService.add_reference_file(DocumentService.DOCUMENT_LIST,
                                                file.read())
        file.close()

        file_path = os.path.join(app.root_path, 'static', 'reference', 'investigators.xlsx')
        file = open(file_path, "rb")
        ReferenceFileService.add_reference_file(StudyService.INVESTIGATOR_LIST,
                                                file.read())
        file.close()

    def load_default_user(self):
        ldap_info = LdapModel(uid="dhf8r", email_address="dhf8r@virginia.edu", display_name="Development User")
        user = UserModel(uid="dhf8r", ldap_info=ldap_info)
        db.session.add(ldap_info)
        db.session.add(user)
        db.session.commit()

def ldap(): return "x";
def study_info(i): return {"x":"Y"};


me = ldap()
investigators = study_info('investigators')
pi = investigators.get('PI', None)
is_me_pi = False
if pi is not None:
    hasPI = True
    if pi['uid'] == me['uid']:
        is_me_pi = True
else:
    hasPI = False

dc = investigators.get('DEPT_CH', None)
pcs = {}
is_me_pc = False
for k in investigators.keys():
    if k in ['SC_I','SC_II','IRBC']:
        investigator = investigators.get(k)
        if investigator['uid'] != me['uid']:
            pcs[k] = investigator
        else:
            is_me_pc = True
            is_me_pc_role = investigator['label']
        del(investigator)
cnt_pcs = len(pcs.keys())
acs = {}
is_me_ac = False
for k in investigators.keys():
    if k == 'AS_C':
        investigator = investigators.get(k)
        if investigator['uid'] != me['uid']:
            acs[k] = investigator
        else:
            is_me_ac = True
            is_me_ac_role = investigator['label']
        del investigator

cnt_acs = len(acs.keys())
subs = {}
is_me_subs = False
for k in investigators.keys():
    if k[:2] == 'SI':
        investigator = investigators.get(k)
        if investigator['uid'] != me['uid']:
            subs[k] = investigator
        else:
            is_me_subs = True
        del investigator

cnt_subs = len(subs.keys())
del investigators

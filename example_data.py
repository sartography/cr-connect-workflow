import datetime
import glob
import os

from crc import app, db, session
from crc.models.file import FileType, FileModel, FileDataModel
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowSpecModel


class ExampleDataLoader:
    def make_data(self):
        studies = [
            StudyModel(
                id=1,
                title='The impact of fried pickles on beer consumption in bipedal software developers.',
                last_updated=datetime.datetime.now(),
                protocol_builder_status='in_process',
                primary_investigator_id='dhf8r',
                sponsor='Sartography Pharmaceuticals',
                ind_number='1234'
            ),
            StudyModel(
                id=2,
                title='Requirement of hippocampal neurogenesis for the behavioral effects of soft pretzels',
                last_updated=datetime.datetime.now(),
                protocol_builder_status='in_process',
                primary_investigator_id='dhf8r',
                sponsor='Makerspace & Co.',
                ind_number='5678'
            ),
        ]

        workflow_specifications = \
            self.create_spec(id="random_fact",
                             name="random_fact",
                             display_name="Random Fact Generator",
                             description='Displays a random fact about a topic of your choosing.')
        workflow_specifications += \
            self.create_spec(id="two_forms",
                             name="two_forms",
                             display_name="Two dump questions on two separate tasks",
                             description='the name says it all')
        workflow_specifications += \
            self.create_spec(id="decision_table",
                             name="decision_table",
                             display_name="Form with Decision Table",
                             description='the name says it all')
        workflow_specifications += \
            self.create_spec(id="parallel_tasks",
                             name="parallel_tasks",
                             display_name="Parallel tasks",
                             description='Four tasks that can happen simultaneously')
        workflow_specifications += \
            self.create_spec(id="exclusive_gateway",
                             name="exclusive_gateway",
                             display_name="Exclusive Gateway Example",
                             description='How to take different paths based on input.')

#        workflow_specifications += \
#            self.create_spec(id="docx",
#                             name="docx",
#                             display_name="Form with document generation",
#                             description='the name says it all')

        all_data = studies + workflow_specifications
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
#            elif file_extension.lower() == '.docx':
#                type = FileType.docx
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
                models.append(FileDataModel(data=file.read(), file_model=file_model))
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

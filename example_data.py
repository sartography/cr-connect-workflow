import datetime
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
                             display_name="Random Fact Generator",
                             description='Displays a random fact about a topic of your choosing.')
        workflow_specifications += \
            self.create_spec(id="two_forms",
                             display_name="Two dump questions on two seperate tasks",
                             description='Displays a random fact about a topic of your choosing.')

        all_data = studies + workflow_specifications
        return all_data

    def create_spec(self, id, display_name, description):
        """Assumes that a file exists in static/bpmn with the same name as the given id.
           returns an array of data models to be added to the database."""
        spec = WorkflowSpecModel(id=id,
                                 display_name=display_name,
                                 description=description)
        file_model = FileModel(name=id + ".bpmn", type=FileType.bpmn, content_type='text/xml', version="1",
                               last_updated=datetime.datetime.now(), primary=True,
                               workflow_spec_id=id)
        filename = os.path.join(app.root_path, 'static', 'bpmn', id + ".bpmn")
        file = open(filename, "rb")
        workflow_data = FileDataModel(data=file.read(), file_model=file_model)
        file.close()
        return [spec, file_model, workflow_data]

    @staticmethod
    def clean_db():
        session.flush()  # Clear out any transactions before deleting it all to avoid spurious errors.
        for table in reversed(db.metadata.sorted_tables):
            session.execute(table.delete())
        session.flush()

    def load_all(self):
        session.add_all(self.make_data())
        session.commit()
        session.flush()

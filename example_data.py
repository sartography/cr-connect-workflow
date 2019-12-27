import datetime
import os

from crc import db, app
from crc.models import StudyModel, WorkflowSpecModel, FileType, FileModel, FileDataModel


class ExampleDataLoader:
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

    workflow_specs = [WorkflowSpecModel(
        id="random_fact",
        display_name="Random Fact Generator",
        description='Displays a random fact about a topic of your choosing.',
    )]

    workflow_spec_files = [WorkflowSpecModel(
        id="random_fact",
        display_name="Random Fact Generator",
        description='Displays a random fact about a topic of your choosing.',
    )]

    workflow_spec_files = [FileModel(name="random_fact.bpmn",
                                     type=FileType.bpmn,
                                     version="1",
                                     last_updated=datetime.datetime.now(),
                                     primary=True,
                                     workflow_spec_id=workflow_specs[0].id)]

    filename = os.path.join(app.root_path, 'static', 'bpmn', 'random_fact', 'random_fact.bpmn')
    file = open(filename, "rb")
    workflow_data = [FileDataModel(data=file.read(), file_model=workflow_spec_files[0])]

    def load_all(self):
        db.session.bulk_save_objects(ExampleDataLoader.studies)
        db.session.bulk_save_objects(ExampleDataLoader.workflow_specs)
        db.session.bulk_save_objects(ExampleDataLoader.workflow_spec_files)
        db.session.bulk_save_objects(ExampleDataLoader.workflow_data)

        db.session.commit()

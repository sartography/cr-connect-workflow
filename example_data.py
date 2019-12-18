import datetime

from crc import db
from crc.models import StudyModel, WorkflowSpecModel


class ExampleDataLoader:
    studies = [StudyModel(id=1,
                          title='The impact of fried pickles on beer consumption in bipedal software developers.',
                          last_updated=datetime.datetime.now(),
                          protocol_builder_status='in_process',
                          primary_investigator_id='dhf8r',
                          sponsor='Sartography Pharmaceuticals',
                          ind_number='1234')]

    workflow_specs = [WorkflowSpecModel(
        id="random_fact",
        display_name="Random Fact Generator",
        description='Displays a random fact about a topic of your choosing.',
    )]

    def load_all(self):
        db.session.bulk_save_objects(ExampleDataLoader.studies)
        db.session.bulk_save_objects(ExampleDataLoader.workflow_specs)
        db.session.commit()

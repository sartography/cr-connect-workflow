import glob
import os

from crc import app, db, session
from crc.models.file import CONTENT_TYPES
from crc.models.workflow import WorkflowSpecInfo
from crc.services.document_service import DocumentService
from crc.services.reference_file_service import ReferenceFileService
from crc.services.spec_file_service import SpecFileService
from crc.services.study_service import StudyService


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

    def create_spec(self, id, display_name="", description="", filepath=None, master_spec=False,
                    category_id=None, display_order=None, from_tests=False, standalone=False, library=False):
        """Assumes that a directory exists in static/bpmn with the same name as the given id.
           further assumes that the [id].bpmn is the primary file for the workflow.
           returns an array of data models to be added to the database."""
        global file
        spec = WorkflowSpecInfo(id=id,
                                display_name=display_name,
                                description=description,
                                category_name=category_id,
                                display_order=display_order,
                                is_master_spec=master_spec,
                                standalone=standalone,
                                library=library,
                                primary_file_name="",
                                primary_process_id="",
                                is_review=False,
                                libraries=[])
        db.session.add(spec)
        db.session.commit()
        if not filepath and not from_tests:
            filepath = os.path.join(app.root_path, 'static', 'bpmn', id, "*.*")
        if not filepath and from_tests:
            filepath = os.path.join(app.root_path, '..', 'tests', 'data', id, "*.*")

        files = glob.glob(filepath)
        for file_path in files:
            if os.path.isdir(file_path):
                continue  # Don't try to process sub directories

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

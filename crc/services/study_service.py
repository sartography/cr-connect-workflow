from typing import List

from SpiffWorkflow import WorkflowException

from crc import db, session
from crc.api.common import ApiError
from crc.models.file import FileModel
from crc.models.protocol_builder import ProtocolBuilderStudy, ProtocolBuilderStatus
from crc.models.stats import WorkflowStatsModel, TaskEventModel
from crc.models.study import StudyModel, Study, Category, WorkflowMetadata
from crc.models.workflow import WorkflowSpecCategoryModel, WorkflowModel, WorkflowSpecModel, WorkflowState, \
    WorkflowStatus
from crc.scripts.documents import Documents
from crc.services.file_service import FileService
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.workflow_processor import WorkflowProcessor


class StudyService(object):
    """Provides common tools for working with a Study"""

    @staticmethod
    def get_studies_for_user(user):
        """Returns a list of all studies for the given user."""
        db_studies = session.query(StudyModel).filter_by(user_uid=user.uid).all()
        studies = []
        for study_model in db_studies:
            studies.append(StudyService.get_study(study_model.id, study_model))
        return studies

    @staticmethod
    def get_study(study_id, study_model: StudyModel = None):
        """Returns a study model that contains all the workflows organized by category.
        IMPORTANT:  This is intended to be a lightweight call, it should never involve
        loading up and executing all the workflows in a study to calculate information."""
        if not study_model:
            study_model = session.query(StudyModel).filter_by(id=study_id).first()
        study = Study.from_model(study_model)
        study.categories = StudyService.get_categories()
        workflow_metas = StudyService.__get_workflow_metas(study_id)
        status = StudyService.__get_study_status(study_model)
        study.warnings = StudyService.__update_status_of_workflow_meta(workflow_metas, status)

        # Group the workflows into their categories.
        for category in study.categories:
            category.workflows = {w for w in workflow_metas if w.category_id == category.id}

        return study

    @staticmethod
    def delete_study(study_id):
        session.query(WorkflowStatsModel).filter_by(study_id=study_id).delete()
        session.query(TaskEventModel).filter_by(study_id=study_id).delete()
        session.query(WorkflowModel).filter_by(study_id=study_id).delete()
        session.query(StudyModel).filter_by(id=study_id).delete()
        session.commit()

    @staticmethod
    def get_categories():
        """Returns a list of category objects, in the correct order."""
        cat_models = db.session.query(WorkflowSpecCategoryModel) \
            .order_by(WorkflowSpecCategoryModel.display_order).all()
        categories = []
        for cat_model in cat_models:
            categories.append(Category(cat_model))
        return categories

    @staticmethod
    def get_approvals(study_id):
        """Returns a list of approval workflows."""
        cat = session.query(WorkflowSpecCategoryModel).filter_by(name="approvals").first()
        specs = session.query(WorkflowSpecModel).filter_by(category_id=cat.id).all()
        spec_ids = [spec.id for spec in specs]
        workflows = session.query(WorkflowModel) \
            .filter(WorkflowModel.study_id == study_id) \
            .filter(WorkflowModel.workflow_spec_id.in_(spec_ids)) \
            .all()

        approvals = []
        for workflow in workflows:
            workflow: WorkflowModel = workflow
            approvals.append({
                'id': workflow.id,
                'display_name': workflow.workflow_spec.display_name,
                'name': workflow.workflow_spec.display_name,
                'status': workflow.status.value,
                'workflow_spec_id': workflow.workflow_spec_id,
            })
        return approvals

    @staticmethod
    def get_documents_status(study_id):
        """Returns a list of required documents and related workflow status."""
        doc_service = Documents()

        # Get PB required docs
        pb_docs = ProtocolBuilderService.get_required_docs(study_id)

        # Get required docs for study
        study_docs = doc_service.get_documents(study_id=study_id, pb_docs=pb_docs)

        # Container for results
        documents = []

        # For each required doc, get file(s)
        for code, doc in study_docs.items():
            doc['study_id'] = study_id
            doc['code'] = code
            doc_files = FileService.get_files(study_id=study_id, irb_doc_code=code)

            # For each file, get associated workflow status
            for file in doc_files:
                doc['file_id'] = file.id
                doc['workflow_id'] = file.workflow_id

                if doc['status'] is None:
                    workflow: WorkflowModel = session.query(WorkflowModel).filter_by(id=file.workflow_id).first()
                    doc['status'] = workflow.status.value

            documents.append(doc)

        return documents

    @staticmethod
    def synch_all_studies_with_protocol_builder(user):
        """Assures that the studies we have locally for the given user are
        in sync with the studies available in protocol builder. """
        # Get studies matching this user from Protocol Builder
        pb_studies: List[ProtocolBuilderStudy] = ProtocolBuilderService.get_studies(user.uid)

        # Get studies from the database
        db_studies = session.query(StudyModel).filter_by(user_uid=user.uid).all()

        # Update all studies from the protocol builder, create new studies as needed.
        # Futher assures that every active study (that does exist in the protocol builder)
        # has a reference to every available workflow (though some may not have started yet)
        for pb_study in pb_studies:
            db_study = next((s for s in db_studies if s.id == pb_study.STUDYID), None)
            if not db_study:
                db_study = StudyModel(id=pb_study.STUDYID)
                session.add(db_study)
                db_studies.append(db_study)
            db_study.update_from_protocol_builder(pb_study)
            StudyService._add_all_workflow_specs_to_study(db_study)

        # Mark studies as inactive that are no longer in Protocol Builder
        for study in db_studies:
            pb_study = next((pbs for pbs in pb_studies if pbs.STUDYID == study.id), None)
            if not pb_study:
                study.protocol_builder_status = ProtocolBuilderStatus.ABANDONED

        db.session.commit()

    @staticmethod
    def __update_status_of_workflow_meta(workflow_metas, status):
        # Update the status on each workflow
        warnings = []
        for wfm in workflow_metas:
            if wfm.name in status.keys():
                if not WorkflowState.has_value(status[wfm.name]):
                    warnings.append(ApiError("invalid_status",
                                             "Workflow '%s' can not be set to '%s', should be one of %s" % (
                                                 wfm.name, status[wfm.name], ",".join(WorkflowState.list())
                                             )))
                else:
                    wfm.state = WorkflowState[status[wfm.name]]
            else:
                warnings.append(ApiError("missing_status", "No status specified for workflow %s" % wfm.name))
        return warnings

    @staticmethod
    def __get_workflow_metas(study_id):
        # Add in the Workflows for each category
        workflow_models = db.session.query(WorkflowModel). \
            join(WorkflowSpecModel). \
            filter(WorkflowSpecModel.is_master_spec == False). \
            filter(WorkflowModel.study_id == study_id). \
            all()
        workflow_metas = []
        for workflow in workflow_models:
            workflow_metas.append(WorkflowMetadata.from_workflow(workflow))
        return workflow_metas

    @staticmethod
    def __get_study_status(study_model):
        """Uses the Top Level Workflow to calculate the status of the study, and it's
        workflow models."""
        master_specs = db.session.query(WorkflowSpecModel). \
            filter_by(is_master_spec=True).all()
        if len(master_specs) < 1:
            raise ApiError("missing_master_spec", "No specifications are currently marked as the master spec.")
        if len(master_specs) > 1:
            raise ApiError("multiple_master_specs",
                           "There is more than one master specification, and I don't know what to do.")

        return WorkflowProcessor.run_master_spec(master_specs[0], study_model)

    @staticmethod
    def _add_all_workflow_specs_to_study(study):
        existing_models = session.query(WorkflowModel).filter(WorkflowModel.study_id == study.id).all()
        existing_specs = list(m.workflow_spec_id for m in existing_models)
        new_specs = session.query(WorkflowSpecModel). \
            filter(WorkflowSpecModel.is_master_spec == False). \
            filter(WorkflowSpecModel.id.notin_(existing_specs)). \
            all()
        errors = []
        for workflow_spec in new_specs:
            try:
                StudyService._create_workflow_model(study, workflow_spec)
            except WorkflowException as we:
                errors.append(ApiError.from_task_spec("workflow_execution_exception", str(we), we.sender))
        return errors

    @staticmethod
    def _create_workflow_model(study, spec):
        workflow_model = WorkflowModel(status=WorkflowStatus.not_started,
                                       study_id=study.id,
                                       workflow_spec_id=spec.id)
        session.add(workflow_model)
        session.commit()
        return workflow_model

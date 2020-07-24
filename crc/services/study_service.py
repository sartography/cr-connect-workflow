from copy import copy
from datetime import datetime
import json
from typing import List

import requests
from SpiffWorkflow import WorkflowException
from SpiffWorkflow.exceptions import WorkflowTaskExecException
from ldap3.core.exceptions import LDAPSocketOpenError

from crc import db, session, app
from crc.api.common import ApiError
from crc.models.file import FileModel, FileModelSchema, File
from crc.models.ldap import LdapSchema
from crc.models.protocol_builder import ProtocolBuilderStudy, ProtocolBuilderStatus
from crc.models.task_event import TaskEventModel
from crc.models.study import StudyModel, Study, Category, WorkflowMetadata
from crc.models.workflow import WorkflowSpecCategoryModel, WorkflowModel, WorkflowSpecModel, WorkflowState, \
    WorkflowStatus
from crc.services.file_service import FileService
from crc.services.ldap_service import LdapService
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.approval_service import ApprovalService
from crc.models.approval import Approval


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
    def get_all_studies_with_files():
        """Returns a list of all studies"""
        db_studies = session.query(StudyModel).all()
        studies = []
        for s in db_studies:
            study = Study.from_model(s)
            study.files = FileService.get_files_for_study(study.id)
            studies.append(study)
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
        study.approvals = ApprovalService.get_approvals_for_study(study.id)
        files = FileService.get_files_for_study(study.id)
        files = (File.from_models(model, FileService.get_file_data(model.id),
                         FileService.get_doc_dictionary()) for model in files)
        study.files = list(files)

        # Calling this line repeatedly is very very slow.  It creates the
        # master spec and runs it.  Don't execute this for Abandoned studies, as
        # we don't have the information to process them.
        if study.protocol_builder_status != ProtocolBuilderStatus.ABANDONED:
            status = StudyService.__get_study_status(study_model)
            study.warnings = StudyService.__update_status_of_workflow_meta(workflow_metas, status)

            # Group the workflows into their categories.
            for category in study.categories:
                category.workflows = {w for w in workflow_metas if w.category_id == category.id}

        return study

    @staticmethod
    def delete_study(study_id):
        session.query(TaskEventModel).filter_by(study_id=study_id).delete()
        for workflow in session.query(WorkflowModel).filter_by(study_id=study_id):
            StudyService.delete_workflow(workflow)
        session.query(StudyModel).filter_by(id=study_id).delete()
        session.commit()

    @staticmethod
    def delete_workflow(workflow):
        for file in session.query(FileModel).filter_by(workflow_id=workflow.id).all():
            FileService.delete_file(file.id)
        for dep in workflow.dependencies:
            session.delete(dep)
        session.query(TaskEventModel).filter_by(workflow_id=workflow.id).delete()
        session.query(WorkflowModel).filter_by(id=workflow.id).delete()

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
        """Returns a list of non-hidden approval workflows."""
        study = StudyService.get_study(study_id)
        cat = next(c for c in study.categories if c.name == 'approvals')

        approvals = []
        for wf in cat.workflows:
            if wf.state is WorkflowState.hidden:
                continue

            workflow = db.session.query(WorkflowModel).filter_by(id=wf.id).first()
            approvals.append({
                'study_id': study_id,
                'workflow_id': wf.id,
                'display_name': wf.display_name,
                'display_order': wf.display_order or 0,
                'name': wf.name,
                'state': wf.state.value,
                'status': wf.status.value,
                'workflow_spec_id': workflow.workflow_spec_id,
            })

        approvals.sort(key=lambda k: k['display_order'])
        return approvals

    @staticmethod
    def get_documents_status(study_id):
        """Returns a list of documents related to the study, and any file information
        that is available.."""

        # Get PB required docs, if Protocol Builder Service is enabled.
        if ProtocolBuilderService.is_enabled() and study_id is not None:
            try:
                pb_docs = ProtocolBuilderService.get_required_docs(study_id=study_id)
            except requests.exceptions.ConnectionError as ce:
                app.logger.error(f'Failed to connect to the Protocol Builder - {str(ce)}', exc_info=True)
                pb_docs = []
        else:
            pb_docs = []

        # Loop through all known document types, get the counts for those files,
        # and use pb_docs to mark those as required.
        doc_dictionary = FileService.get_reference_data(FileService.DOCUMENT_LIST, 'code', ['id'])

        documents = {}
        for code, doc in doc_dictionary.items():

            if ProtocolBuilderService.is_enabled():
                pb_data = next((item for item in pb_docs if int(item['AUXDOCID']) == int(doc['id'])), None)
                doc['required'] = False
                if pb_data:
                    doc['required'] = True

            doc['study_id'] = study_id
            doc['code'] = code

            # Make a display name out of categories
            name_list = []
            for cat_key in ['category1', 'category2', 'category3']:
                if doc[cat_key] not in ['', 'NULL']:
                    name_list.append(doc[cat_key])
            doc['display_name'] = ' / '.join(name_list)

            # For each file, get associated workflow status
            doc_files = FileService.get_files_for_study(study_id=study_id, irb_doc_code=code)
            doc['count'] = len(doc_files)
            doc['files'] = []
            for file in doc_files:
                doc['files'].append({'file_id': file.id,
                                     'workflow_id': file.workflow_id})

                # update the document status to match the status of the workflow it is in.
                if 'status' not in doc or doc['status'] is None:
                    workflow: WorkflowModel = session.query(WorkflowModel).filter_by(id=file.workflow_id).first()
                    doc['status'] = workflow.status.value

            documents[code] = doc
        return documents

    @staticmethod
    def get_investigators(study_id, all=False):
        """Convert array of investigators from protocol builder into a dictionary keyed on the type. """

        # Loop through all known investigator types as set in the reference file
        inv_dictionary = FileService.get_reference_data(FileService.INVESTIGATOR_LIST, 'code')

        # Get PB required docs
        pb_investigators = ProtocolBuilderService.get_investigators(study_id=study_id)

        # It is possible for the same type to show up more than once in some circumstances, in those events
        # append a counter to the name.
        investigators = {}
        for i_type in inv_dictionary:
            pb_data_entries = list(item for item in pb_investigators if item['INVESTIGATORTYPE'] == i_type)
            entry_count = 0
            investigators[i_type] = copy(inv_dictionary[i_type])
            investigators[i_type]['user_id'] = None
            for pb_data in pb_data_entries:
                entry_count += 1
                if entry_count == 1:
                    t = i_type
                else:
                    t = i_type + "_" + str(entry_count)
                investigators[t] = copy(inv_dictionary[i_type])
                investigators[t]['user_id'] = pb_data["NETBADGEID"]
                investigators[t].update(StudyService.get_ldap_dict_if_available(pb_data["NETBADGEID"]))
        if not all:
            investigators = dict(filter(lambda elem: elem[1]['user_id'] is not None, investigators.items()))
        return investigators

    @staticmethod
    def get_ldap_dict_if_available(user_id):
        try:
            return LdapSchema().dump(LdapService().user_info(user_id))
        except ApiError as ae:
            app.logger.info(str(ae))
            return {"error": str(ae)}
        except LDAPSocketOpenError:
            app.logger.info("Failed to connect to LDAP Server.")
            return {}

    @staticmethod
    def get_protocol(study_id):
        """Returns the study protocol, if it has been uploaded."""
        file = db.session.query(FileModel)\
            .filter_by(study_id=study_id)\
            .filter_by(form_field_key='Study_Protocol_Document')\
            .first()

        return FileModelSchema().dump(file)

    @staticmethod
    def synch_with_protocol_builder_if_enabled(user):
        """Assures that the studies we have locally for the given user are
        in sync with the studies available in protocol builder. """

        if ProtocolBuilderService.is_enabled():

            app.logger.info("The Protocol Builder is enabled. app.config['PB_ENABLED'] = " +
                            str(app.config['PB_ENABLED']))

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
    def _add_all_workflow_specs_to_study(study_model:StudyModel):
        existing_models = session.query(WorkflowModel).filter(WorkflowModel.study == study_model).all()
        existing_specs = list(m.workflow_spec_id for m in existing_models)
        new_specs = session.query(WorkflowSpecModel). \
            filter(WorkflowSpecModel.is_master_spec == False). \
            filter(WorkflowSpecModel.id.notin_(existing_specs)). \
            all()
        errors = []
        for workflow_spec in new_specs:
            try:
                StudyService._create_workflow_model(study_model, workflow_spec)
            except WorkflowTaskExecException as wtee:
                errors.append(ApiError.from_task("workflow_startup_exception", str(wtee), wtee.task))
            except WorkflowException as we:
                errors.append(ApiError.from_task_spec("workflow_startup_exception", str(we), we.sender))
        return errors

    @staticmethod
    def _create_workflow_model(study: StudyModel, spec):
        workflow_model = WorkflowModel(status=WorkflowStatus.not_started,
                                       study=study,
                                       workflow_spec_id=spec.id,
                                       last_updated=datetime.now())
        session.add(workflow_model)
        session.commit()
        return workflow_model

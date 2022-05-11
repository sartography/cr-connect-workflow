from copy import copy
from datetime import datetime
from dateutil import parser
from typing import List

import requests
from SpiffWorkflow import WorkflowException
from SpiffWorkflow.bpmn.PythonScriptEngine import Box
from SpiffWorkflow.exceptions import WorkflowTaskExecException
from SpiffWorkflow.util.metrics import timeit, firsttime, sincetime, LOG
from flask import g
from ldap3.core.exceptions import LDAPSocketOpenError

from crc import db, session, app
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.email import EmailModel
from crc.models.file import FileModel, File, FileSchema
from crc.models.ldap import LdapSchema

from crc.models.protocol_builder import ProtocolBuilderCreatorStudy
from crc.models.study import StudyModel, Study, StudyStatus, Category, WorkflowMetadata, StudyEventType, StudyEvent, \
    StudyAssociated, ProgressStatus, CategoryMetadata
from crc.models.task_event import TaskEventModel
from crc.models.task_log import TaskLogModel
from crc.models.workflow import WorkflowSpecCategory, WorkflowModel, WorkflowSpecInfo, WorkflowState, \
    WorkflowStatus
from crc.services.document_service import DocumentService
from crc.services.ldap_service import LdapService
from crc.services.lookup_service import LookupService
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.user_file_service import UserFileService
from crc.services.workflow_processor import WorkflowProcessor


class StudyService(object):
    """Provides common tools for working with a Study"""
    INVESTIGATOR_LIST = "investigators.xlsx"  # A reference document containing details about what investigators to show, and when.

    # The review types 2, 3, 21 correspond to review type names
    # `Full Committee`, `Expedited`, and `Review by Non-UVA IRB`
    # These are considered to be the valid review types that can be shown to users.
    VALID_REVIEW_TYPES = [2, 3, 21]
    PB_MIN_DATE = parser.parse(app.config['PB_MIN_DATE'])

    def get_studies_for_user(self, user, categories, include_invalid=False):
        """Returns a list of all studies for the given user."""

        associated = session.query(StudyAssociated).filter_by(uid=user.uid, access=True).all()
        associated_studies = [x.study_id for x in associated]
        db_studies = session.query(StudyModel).filter((StudyModel.user_uid == user.uid) |
                                                      (StudyModel.id.in_(associated_studies))).all()

        studies = []
        for study_model in db_studies:
            if include_invalid or study_model.review_type in self.VALID_REVIEW_TYPES:
                studies.append(StudyService.get_study(study_model.id, categories, study_model=study_model,
                                                      process_categories=False))
        return studies

    @staticmethod
    def get_all_studies_with_files():
        """Returns a list of all studies"""
        db_studies = session.query(StudyModel).all()
        studies = []
        for s in db_studies:
            study = Study.from_model(s)
            study.files = UserFileService.get_files_for_study(study.id)
            studies.append(study)
        return studies

    @staticmethod
    def get_study_warnings(workflow_metas, status):

        # Grab warnings generated from the master workflow for debugging
        warnings = []
        unused_statuses = status.copy()  # A list of all the statuses that are not used.
        for wfm in workflow_metas:
            unused_statuses.pop(wfm.workflow_spec_id, None)
            wfm.state_message = ''
            # do we have a status for you
            if wfm.workflow_spec_id not in status.keys():
                warnings.append(ApiError("missing_status",
                                         "No status information provided about workflow %s" % wfm.workflow_spec_id))
                continue
            if not isinstance(status[wfm.workflow_spec_id], dict):
                warnings.append(ApiError(code='invalid_status',
                                         message=f'Status must be a dictionary with "status" and "message" keys. '
                                                 f'Name is {wfm.workflow_spec_id}. Status is {status[wfm.workflow_spec_id]}'))
                continue
            if 'status' not in status[wfm.workflow_spec_id].keys():
                warnings.append(ApiError("missing_status_key",
                                         "Workflow '%s' is present in master workflow, but doesn't have a status" % wfm.workflow_spec_id))
                continue
            if not WorkflowState.has_value(status[wfm.workflow_spec_id]['status']):
                warnings.append(ApiError("invalid_state",
                                         "Workflow '%s' can not be set to '%s', should be one of %s" % (
                                             wfm.workflow_spec_id, status[wfm.workflow_spec_id]['status'],
                                             ",".join(WorkflowState.list())
                                         )))
                continue

        for status in unused_statuses:
            if isinstance(unused_statuses[status], dict) and 'status' in unused_statuses[status]:
                warnings.append(ApiError("unmatched_status", "The master workflow provided a status for '%s' a "
                                                             "workflow that doesn't seem to exist." %
                                         status))

        return warnings

    @staticmethod
    @timeit
    def get_study(study_id, categories: List[WorkflowSpecCategory], study_model: StudyModel = None,
                  master_workflow_results=None, process_categories=False):
        """Returns a study model that contains all the workflows organized by category.
        Pass in the results of the master workflow spec, and the status of other workflows will be updated."""
        last_time = firsttime()
        if not study_model:
            study_model = session.query(StudyModel).filter_by(id=study_id).first()
        study = Study.from_model(study_model)
        last_time = sincetime("from model", last_time)
        study.create_user_display = LdapService.user_info(study.user_uid).display_name
        last_time = sincetime("user", last_time)
        last_event: TaskEventModel = session.query(TaskEventModel) \
            .filter_by(study_id=study_id, action='COMPLETE') \
            .order_by(TaskEventModel.date.desc()).first()
        if last_event is None:
            study.last_activity_user = 'Not Started'
            study.last_activity_date = ""
        else:
            study.last_activity_user = LdapService.user_info(last_event.user_uid).display_name
            study.last_activity_date = last_event.date
        last_time = sincetime("task_events", last_time)
        study.categories = categories
        files = UserFileService.get_files_for_study(study.id)
        files = (File.from_file_model(model, DocumentService.get_dictionary()) for model in files)
        study.files = list(files)
        last_time = sincetime("files", last_time)
        if process_categories and master_workflow_results:
            if study.status != StudyStatus.abandoned:
                for category in study.categories:
                    workflow_metas = StudyService._get_workflow_metas(study_id, category)
                    category_meta = []
                    if master_workflow_results:
                        study.warnings = StudyService.get_study_warnings(workflow_metas, master_workflow_results)
                        category_meta = StudyService._update_status_of_category_meta(master_workflow_results, category)
                    category.workflows = workflow_metas
                    category.meta = category_meta
            last_time = sincetime("categories", last_time)

        if study.primary_investigator is None:
            associates = StudyService().get_study_associates(study.id)
            for associate in associates:
                if associate.role == "Primary Investigator":
                    study.primary_investigator = associate.ldap_info.display_name

        # Calculate study progress and return it as a integer out of a hundred
        all_workflows = db.session.query(WorkflowModel).\
            filter(WorkflowModel.study_id == study.id).\
            count()
        complete_workflows = db.session.query(WorkflowModel).\
            filter(WorkflowModel.study_id == study.id).\
            filter(WorkflowModel.status == WorkflowStatus.complete).\
            count()
        if all_workflows > 0:
            study.progress = int((complete_workflows/all_workflows)*100)

        return study

    @staticmethod
    def _get_workflow_metas(study_id, category):
        # Add in the Workflows for each category
        workflow_metas = []
        for spec in category.specs:
            workflow_models = db.session.query(WorkflowModel).\
                filter(WorkflowModel.study_id == study_id).\
                filter(WorkflowModel.workflow_spec_id == spec.id).\
                all()
            for workflow in workflow_models:
                workflow_metas.append(WorkflowMetadata.from_workflow(workflow, spec))
        return workflow_metas


    @staticmethod
    def get_study_associate(study_id=None, uid=None):
        """
        gets details on how one uid is related to a study, returns a StudyAssociated model
        """
        study = db.session.query(StudyModel).filter(StudyModel.id == study_id).first()

        if study is None:
            raise ApiError('study_not_found', 'No study found with id = %d' % study_id)

        if uid is None:
            raise ApiError('uid not specified', 'A valid uva uid is required for this function')

        if uid == study.user_uid:
            return StudyAssociated(uid=uid, role='owner', send_email=True, access=True)

        people = db.session.query(StudyAssociated).filter((StudyAssociated.study_id == study_id) &
                                                          (StudyAssociated.uid == uid)).first()
        if people:
            return people
        else:
            raise ApiError('uid_not_associated_with_study', "user id %s was not associated with study number %d" % (uid,
                                                                                                                    study_id))

    @staticmethod
    def get_study_associates(study_id):
        """
        gets all associated people for a study from the database
        """
        study = db.session.query(StudyModel).filter(StudyModel.id == study_id).first()

        if study is None:
            raise ApiError('study_not_found', 'No study found with id = %d' % study_id)

        people = db.session.query(StudyAssociated).filter(StudyAssociated.study_id == study_id).all()
        ldap_info = LdapService.user_info(study.user_uid)
        owner = StudyAssociated(uid=study.user_uid, role='owner', send_email=True, access=True,
                                ldap_info=ldap_info)
        people.append(owner)
        return people

    @staticmethod
    def update_study_associates(study_id, associates):
        """
        updates the list of associates in the database for a study_id and a list
        of dicts that contains associates
        """
        if study_id is None:
            raise ApiError('study_id not specified', "This function requires the study_id parameter")

        for person in associates:
            if not LdapService.user_exists(person.get('uid', 'impossible_uid')):
                if person.get('uid', 'impossible_uid') == 'impossible_uid':
                    raise ApiError('associate with no uid', 'One of the associates passed as a parameter doesnt have '
                                                            'a uid specified')
                raise ApiError('trying_to_grant_access_to_user_not_found_in_ldap', "You are trying to grant access to "
                                                                                   "%s, but that user was not found in "
                                                                                   "ldap "
                                                                                   "- please check to ensure it is a "
                                                                                   "valid uva uid" % person.get('uid'))

        study = db.session.query(StudyModel).filter(StudyModel.id == study_id).first()
        if study is None:
            raise ApiError('study_id not found', "A study with id# %d was not found" % study_id)

        db.session.query(StudyAssociated).filter(StudyAssociated.study_id == study_id).delete()
        for person in associates:
            newAssociate = StudyAssociated()
            newAssociate.study_id = study_id
            newAssociate.uid = person['uid']
            newAssociate.role = person.get('role', None)
            newAssociate.send_email = person.get('send_email', False)
            newAssociate.access = person.get('access', False)
            session.add(newAssociate)
        session.commit()

    @staticmethod
    def update_study_associate(study_id=None, uid=None, role="", send_email=False, access=False):
        if study_id is None:
            raise ApiError('study_id not specified', "This function requires the study_id parameter")
        if uid is None:
            raise ApiError('uid not specified', "This function requires a uva uid parameter")

        if not LdapService.user_exists(uid):
            raise ApiError('trying_to_grant_access_to_user_not_found_in_ldap', "You are trying to grant access to "
                                                                               "%s but they were not found in ldap "
                                                                               "- please check to ensure it is a "
                                                                               "valid uva uid" % uid)
        study = db.session.query(StudyModel).filter(StudyModel.id == study_id).first()
        if study is None:
            raise ApiError('study_id not found', "A study with id# %d was not found" % study_id)

        assoc = db.session.query(StudyAssociated).filter((StudyAssociated.study_id == study_id) &
                                                         (StudyAssociated.uid == uid) &
                                                         (StudyAssociated.role == role)).first()
        if not assoc:
            assoc = StudyAssociated()

        assoc.study_id = study_id
        assoc.uid = uid
        assoc.role = role
        assoc.send_email = send_email
        assoc.access = access
        session.add(assoc)
        session.commit()
        return True

    @staticmethod
    def delete_study(study_id):
        session.query(TaskEventModel).filter_by(study_id=study_id).delete()
        session.query(TaskLogModel).filter_by(study_id=study_id).delete()
        session.query(StudyAssociated).filter_by(study_id=study_id).delete()
        session.query(EmailModel).filter_by(study_id=study_id).delete()
        session.query(StudyEvent).filter_by(study_id=study_id).delete()
        session.query(DataStoreModel).filter_by(study_id=study_id).delete()
        for workflow in session.query(WorkflowModel).filter_by(study_id=study_id):
            StudyService.delete_workflow(workflow.id)
        study = session.query(StudyModel).filter_by(id=study_id).first()
        session.delete(study)
        session.commit()

    @staticmethod
    def delete_workflow(workflow_id):
        workflow = session.query(WorkflowModel).get(workflow_id)
        if not workflow:
            return

        session.query(TaskEventModel).filter_by(workflow_id=workflow.id).delete()
        files = session.query(FileModel).filter_by(workflow_id=workflow_id).all()
        for file in files:
            session.query(DataStoreModel).filter(DataStoreModel.file_id == file.id).delete()
            session.delete(file)

        session.delete(workflow)
        session.commit()

    @classmethod
    def get_documents_status(cls, study_id, force=False):
        """Returns a list of documents related to the study, and any file information
        that is available.  This is a fairly expensive operation.  So we cache the results
        in Flask's g.  Each fresh api request will get an up to date list, but we won't
        re-create it sevearl times."""
        if 'doc_statuses' not in g:
            g.doc_statuses = {}
        if study_id not in g.doc_statuses or force:
            g.doc_statuses[study_id] = StudyService.__get_documents_status(study_id)
        return g.doc_statuses[study_id]


    @staticmethod
    def __get_documents_status(study_id):
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
        doc_dictionary = DocumentService.get_dictionary()

        documents = {}
        study_files = UserFileService.get_files_for_study(study_id=study_id)

        for code, doc in doc_dictionary.items():

            doc['required'] = False
            if ProtocolBuilderService.is_enabled() and doc['id'] != '':
                pb_data = next(
                    (item for item in pb_docs['AUXDOCS'] if int(item['SS_AUXILIARY_DOC_TYPE_ID']) == int(doc['id'])),
                    None)
                if pb_data:
                    doc['required'] = True

            doc['study_id'] = study_id
            doc['code'] = code


            # Make a display name out of categories
            name_list = []
            for cat_key in ['category1', 'category2', 'category3']:
                if doc[cat_key] not in ['', 'NULL', None]:
                    name_list.append(doc[cat_key])
            doc['display_name'] = ' / '.join(name_list)


            # For each file, get associated workflow status
            doc_files = list(filter(lambda f: f.irb_doc_code == code, study_files))
#            doc_files = UserFileService.get_files_for_study(study_id=study_id, irb_doc_code=code)
            doc['count'] = len(doc_files)
            doc['files'] = []


            for file_model in doc_files:
                file = File.from_file_model(file_model, [])
                file_data = FileSchema().dump(file)
                del file_data['document']
                doc['files'].append(Box(file_data))
                # update the document status to match the status of the workflow it is in.
                if 'status' not in doc or doc['status'] is None:
                    status = session.query(WorkflowModel.status).filter_by(id=file.workflow_id).scalar()
                    doc['status'] = status.value

            documents[code] = doc
        return Box(documents)

    @staticmethod
    def get_investigator_dictionary():
        lookup_model = LookupService.get_lookup_model_for_reference(StudyService.INVESTIGATOR_LIST, 'code', 'label')
        doc_dict = {}
        for lookup_data in lookup_model.dependencies:
            doc_dict[lookup_data.value] = lookup_data.data
        return doc_dict

    @staticmethod
    def get_investigators(study_id, all=False):
        """Convert array of investigators from protocol builder into a dictionary keyed on the type. """

        # Loop through all known investigator types as set in the reference file
        inv_dictionary = StudyService.get_investigator_dictionary()

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
    @timeit
    def synch_with_protocol_builder_if_enabled(user, specs):
        """Assures that the studies we have locally for the given user are
        in sync with the studies available in protocol builder. """

        if ProtocolBuilderService.is_enabled():

            app.logger.info("The Protocol Builder is enabled. app.config['PB_ENABLED'] = " +
                            str(app.config['PB_ENABLED']))

            # Get studies matching this user from Protocol Builder
            pb_studies: List[ProtocolBuilderCreatorStudy] = ProtocolBuilderService.get_studies(user.uid)

            # Get studies from the database
            db_studies = session.query(StudyModel).filter_by(user_uid=user.uid).all()

            # Update all studies from the protocol builder, create new studies as needed.
            # Further assures that every active study (that does exist in the protocol builder)
            # has a reference to every available workflow (though some may not have started yet)
            for pb_study in pb_studies:
                try:
                    if pb_study.DATELASTMODIFIED:
                        last_modified = parser.parse(pb_study.DATELASTMODIFIED)
                    else:
                        last_modified = parser.parse(pb_study.DATECREATED)
                    if last_modified.date() < StudyService.PB_MIN_DATE.date():
                        continue
                except Exception as e:
                    # Last modified is null or undefined.  Don't import it.
                    continue
                new_status = None
                new_progress_status = None
                db_study = session.query(StudyModel).filter(StudyModel.id == pb_study.STUDYID).first()
                #db_study = next((s for s in db_studies if s.id == pb_study.STUDYID), None)

                add_study = False
                if not db_study:
                    db_study = StudyModel(id=pb_study.STUDYID)
                    db_study.status = None  # Force a new sa
                    new_status = StudyStatus.in_progress
                    new_progress_status = ProgressStatus.in_progress

                    # we use add_study below to determine whether we add the study to the session
                    add_study = True
                    db_studies.append(db_study)

                db_study.update_from_protocol_builder(pb_study, user.uid)
                StudyService.add_all_workflow_specs_to_study(db_study, specs)

                # If there is a new automatic status change and there isn't a manual change in place, record it.
                if new_status and db_study.status != StudyStatus.hold:
                    db_study.status = new_status
                    # make sure status is `in_progress`, before processing new automatic progress_status.
                    if new_progress_status and db_study.status == StudyStatus.in_progress:
                        db_study.progress_status = new_progress_status
                    StudyService.add_study_update_event(db_study,
                                                        status=new_status,
                                                        event_type=StudyEventType.automatic)
                # we moved session.add here so that it comes after we update the study
                # we only add if it doesnt already exist in the DB
                if add_study:
                    session.add(db_study)

            # Mark studies as inactive that are no longer in Protocol Builder
            for study in db_studies:
                pb_study = next((pbs for pbs in pb_studies if pbs.STUDYID == study.id), None)
                if not pb_study and study.status != StudyStatus.abandoned:
                    study.status = StudyStatus.abandoned
                    StudyService.add_study_update_event(study,
                                                        status=StudyStatus.abandoned,
                                                        event_type=StudyEventType.automatic)

            db.session.commit()

    @staticmethod
    def add_study_update_event(study, status, event_type, user_uid=None, comment=''):
        study_event = StudyEvent(study=study,
                                 status=status,
                                 event_type=event_type,
                                 user_uid=user_uid,
                                 comment=comment)
        db.session.add(study_event)
        db.session.commit()

    @staticmethod
    def _update_status_of_category_meta(status, cat):
        cat_meta = CategoryMetadata()
        unused_statuses = status.copy()
        if unused_statuses.get(cat.id):
            cat_meta.id = cat.id
            cat_meta.state = WorkflowState[unused_statuses.get(cat.id)['status']].value
            cat_meta.message = unused_statuses.get(cat.id)['message'] \
                if unused_statuses.get(cat.id)['message'] else ''
        return cat_meta

    @staticmethod
    def add_all_workflow_specs_to_study(study_model: StudyModel, specs: List[WorkflowSpecInfo]):
        existing_models = session.query(WorkflowModel).filter(WorkflowModel.study == study_model).all()
        existing_spec_ids = list(map(lambda x: x.workflow_spec_id, existing_models))
        errors = []
        for workflow_spec in specs:
            if workflow_spec.id in existing_spec_ids:
                continue
            try:
                StudyService._create_workflow_model(study_model, workflow_spec)
            except WorkflowException as we:
                errors.append(ApiError.from_workflow_exception("workflow_startup_exception", str(we), we))
        return errors

    @staticmethod
    def _create_workflow_model(study: StudyModel, spec):
        workflow_model = WorkflowModel(status=WorkflowStatus.not_started,
                                       study=study,
                                       user_id=None,
                                       workflow_spec_id=spec.id,
                                       last_updated=datetime.utcnow())
        session.add(workflow_model)
        session.commit()
        return workflow_model

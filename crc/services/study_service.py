from copy import copy
from datetime import datetime, timezone
from dateutil import parser
from typing import List

import requests
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.bpmn.PythonScriptEngine import Box
from SpiffWorkflow.bpmn.exceptions import WorkflowTaskExecException
from flask import g
from ldap3.core.exceptions import LDAPSocketOpenError

from crc import db, session, app
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.email import EmailModel
from crc.models.email import EmailDocCodesModel
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

import time


def time_it(method, last_time=None):
    if app.config['CAN_TIME_IT']:
        now = time.time()
        if last_time:
            app.logger.info(f"{method}: Time since last time: {now - last_time}")
        else:
            app.logger.info(f"{method}: First time: {now}")
        return now


class StudyService(object):
    """Provides common tools for working with a Study"""
    INVESTIGATOR_LIST = "investigators.xlsx"  # A reference document containing details about what investigators to show, and when.

    # The review types 2, 3, 21, 23, 24 correspond to review type names
    # `Full Committee`, `Expedited`, `Review by Non-UVA IRB`, `Non-UVA IRB - Expedited`, and `Non-UVA IRB - Full Board`
    # These are considered to be the valid review types that can be shown to users.
    VALID_REVIEW_TYPES = [2, 3, 21, 23, 24]

    @staticmethod
    def get_study_url(study_id):
        """Returns the URL for a study."""
        base_url = app.config['FRONTEND']
        # TODO: This is a hack to get around the fact that
        #  the backend doesn't know the real url of the frontend.
        #  FRONTEND does not have /app appended to it.
        #  The linux boxes have 2 environment variables for the frontend;
        #  DEPLOY_URL=/app and BASE_HREF=/app.
        #  I don't know how those are used yet
        if app.config['INSTANCE_NAME'] != 'development':
            base_url += '/app'
        return f'https://{base_url}/study/{study_id}'

    @staticmethod
    def get_pb_min_date():
        try:
            pb_min_date = parser.parse(app.config['PB_MIN_DATE'])
        except Exception:
            pb_min_date = datetime(2019, 1, 1)
        return pb_min_date

    def get_studies_for_user(self, user, categories, include_invalid=False):
        """Returns a list of all studies for the given user."""

        # gets studies for the user
        associated = session.query(StudyAssociated).filter_by(uid=user.uid, access=True).all()
        associated_studies = [x.study_id for x in associated]
        db_studies = session.query(StudyModel).filter((StudyModel.user_uid == user.uid) |
                                                      (StudyModel.id.in_(associated_studies))).all()

        # add extra data to display in home page table
        studies = []
        for row in db_studies:
            study_model = row
            if study_model.review_type in self.VALID_REVIEW_TYPES:
                primary_investigator = session.query(StudyAssociated).filter_by(study_id=study_model.id, role='Primary Investigator').first()
                study_model.primary_investigator = primary_investigator.ldap_info.display_name if primary_investigator and primary_investigator.ldap_info else ''
                study_model.last_activity_user, study_model.last_activity_date = self.get_last_user_and_date(study_model.id)
                study_model.create_user_display = LdapService.user_info(study_model.user_uid).display_name
                studies.append(study_model)
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
        """Returns a list of warnings for the study.
        These are generated from the master workflow."""

        # Grab warnings generated from the master workflow for debugging
        warnings = []
        unused_statuses = status.copy()  # A list of all the statuses that are not used.
        for wfm in workflow_metas:
            unused_statuses.pop(wfm.workflow_spec_id, None)
            # do we have a status for you
            if wfm.workflow_spec_id not in status.keys():
                warnings.append(ApiError(
                    "missing_status",
                          f"No status information provided about workflow {wfm.workflow_spec_id}"))
                continue
            if not isinstance(status[wfm.workflow_spec_id], dict):
                warnings.append(ApiError(
                    code='invalid_status',
                    message=f'Status must be a dictionary with "status" and "message" keys. '
                    f'Name is {wfm.workflow_spec_id}. Status is {status[wfm.workflow_spec_id]}'))
                continue
            if 'status' not in status[wfm.workflow_spec_id].keys():
                warnings.append(ApiError(
                    "missing_status_key",
                    f"Workflow '{wfm.workflow_spec_id}' "
                    f"is present in master workflow, but doesn't have a status"))
                continue
            if not WorkflowState.has_value(status[wfm.workflow_spec_id]['status']):
                warnings.append(ApiError(
                    "invalid_state",
                    f"Workflow '{wfm.workflow_spec_id}' "
                    f"can not be set to '{status[wfm.workflow_spec_id]['status']}', "
                    f"should be one of {','.join(WorkflowState.list())}"))

        for unused_status in unused_statuses:
            if (isinstance(unused_statuses[unused_status], dict)
                    and 'status' in unused_statuses[unused_status]):
                warnings.append(ApiError(
                    "unmatched_status",
                    f"The master workflow provided a status for '{unused_status}' "
                    "a workflow that doesn't seem to exist."))

        return warnings

    @staticmethod
    def get_progress_percent(study_id):
        # Calculate study progress and return it as a integer out of a hundred
        all_workflows = db.session.query(WorkflowModel).filter(WorkflowModel.study_id == study_id).count()
        complete_workflows = db.session.query(WorkflowModel).filter(WorkflowModel.study_id == study_id).filter(WorkflowModel.status == WorkflowStatus.complete).count()
        if all_workflows > 0:
            return int((complete_workflows/all_workflows)*100)
        else:
            return 0

    @staticmethod
    def get_last_user_and_date(study_id):
        last_event: TaskEventModel = session.query(TaskEventModel) \
            .filter_by(study_id=study_id, action='COMPLETE') \
            .order_by(TaskEventModel.date.desc()).first()
        if last_event is None:
            last_activity_user = 'Not Started'
            last_activity_date = ""
        else:
            last_activity_user = LdapService.user_info(last_event.user_uid).display_name
            last_activity_date = last_event.date

        return last_activity_user, last_activity_date

    @staticmethod
    def get_study(study_id, categories: List[WorkflowSpecCategory], study_model: StudyModel = None,
                  master_workflow_results=None, process_categories=False):
        """Returns a study model that contains all the workflows organized by category.
        Pass in the results of the master workflow spec, and the status of other workflows will be updated."""
        if not study_model:
            study_model = session.query(StudyModel).filter_by(id=study_id).first()
        study = Study.from_model(study_model)
        study.create_user_display = LdapService.user_info(study.user_uid).display_name
        last_activity_user, last_activity_date = StudyService.get_last_user_and_date(study_id)
        study.last_activity_user = last_activity_user
        study.last_activity_date = last_activity_date
        study.categories = categories
        files = UserFileService.get_files_for_study(study.id)
        files = (File.from_file_model(model, DocumentService.get_dictionary()) for model in files)
        study.files = list(files)
        if process_categories and master_workflow_results is not None:
            if study.status != StudyStatus.abandoned:
                workflow_metas = []
                for category in study.categories:
                    cat_workflow_metas = StudyService._get_workflow_metas(study_id, category)
                    workflow_metas.extend(cat_workflow_metas)
                    category_meta = []
                    if master_workflow_results:
                        category_meta = StudyService._update_status_of_category_meta(master_workflow_results, category)
                    category.workflows = cat_workflow_metas
                    category.meta = category_meta
                study.warnings = StudyService.get_study_warnings(workflow_metas, master_workflow_results)

        if study.primary_investigator is None:
            associates = StudyService().get_study_associates(study.id)
            for associate in associates:
                if associate.role == "Primary Investigator":
                    study.primary_investigator = associate.ldap_info.display_name

        # TODO: We don't use the progress bar. This should be removed.
        # study.progress = StudyService.get_progress_percent(study.id)

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
            raise ApiError('study_id not found', f"A study with id# {study_id} was not found")

        db.session.query(StudyAssociated).filter(StudyAssociated.study_id == study_id).delete()
        for person in associates:
            new_associate = StudyAssociated()
            new_associate.study_id = study_id
            new_associate.uid = person['uid']
            new_associate.role = person.get('role', None)
            new_associate.send_email = person.get('send_email', False)
            new_associate.access = person.get('access', False)
            session.add(new_associate)
        session.commit()

    @staticmethod
    def update_study_associate(study_id=None, uid=None, role="", send_email=False, access=False):
        if study_id is None:
            raise ApiError('study_id not specified', "This function requires the study_id parameter")
        if uid is None:
            raise ApiError('uid not specified', "This function requires a uva uid parameter")

        uid = uid.lower()
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
        for email in session.query(EmailModel).filter_by(study_id=study_id):
            session.query(EmailDocCodesModel).filter_by(email_id=email.id).delete()
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

    def __delete_exempt_study(self, study_id):
        """Remove studies when IRB Review Type is 'Exempt'"""
        self.delete_study(study_id)

    @staticmethod
    def __process_pb_study(pb_study, db_studies, user, specs):
        """Process the information from PB"""
        new_status = None
        new_progress_status = None
        db_study = session.query(StudyModel).filter(StudyModel.id == pb_study.STUDYID).first()

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

        # If there is a new automatic status change and no manual change in place, record it.
        if new_status and db_study.status != StudyStatus.hold:
            db_study.status = new_status
            # make sure status is `in_progress`, before processing new automatic progress_status.
            if new_progress_status and db_study.status == StudyStatus.in_progress:
                db_study.progress_status = new_progress_status
            StudyService.add_study_update_event(db_study,
                                                status=new_status,
                                                event_type=StudyEventType.automatic)
        # we moved session.add here so that it comes after we update the study
        # we only add if it doesn't already exist in the DB
        if add_study:
            session.add(db_study)
            session.commit()

    def __process_pb_studies(self, pb_studies, db_studies, user, specs):
        for pb_study in pb_studies:
            if pb_study.DATECREATED:
                created_date = parser.parse(pb_study.DATECREATED)
            else:
                # we don't import studies that don't have a DATECREATED
                continue
            if created_date.timestamp() < StudyService.get_pb_min_date().timestamp():
                # we don't import old studies
                continue

            self.__process_pb_study(pb_study, db_studies, user, specs)

    @staticmethod
    def __is_exempt(db_study_id):
        # we receive a list, if the study is downloaded to IRB Online
        # otherwise, we receive this object
        # {'DETAIL': 'Study not downloaded to IRB Online.', 'STATUS': 'Error'}
        pb_study_info = ProtocolBuilderService.get_irb_info(db_study_id)
        if isinstance(pb_study_info, list) and len(pb_study_info) > 0:
            if ('IRB_REVIEW_TYPE' in pb_study_info[0] and
                    pb_study_info[0]['IRB_REVIEW_TYPE'] ==
                    'Exempt'):
                return True
        return False

    def __get_missing_and_exempt_studies(self, db_studies, pb_studies):
        """We don't manage exempt studies"""
        db_study_ids = {db_study.id for db_study in db_studies}
        pb_study_ids = {pb_study.STUDYID for pb_study in pb_studies}
        db_studies_not_in_pb = db_study_ids - pb_study_ids
        exempt_studies = set()

        for db_study_id in db_studies_not_in_pb:
            if self.__is_exempt(db_study_id):
                exempt_studies.add(db_study_id)

        missing_studies = db_studies_not_in_pb - exempt_studies

        return missing_studies, exempt_studies

    def __delete_exempt_studies(self, exempt_studies):
        if exempt_studies:
            for exempt_study_id in exempt_studies:
                self.__delete_exempt_study(exempt_study_id)

    @staticmethod
    def __abandon_missing_studies(missing_studies, db_studies):
        for missing_study_id in missing_studies:
            study = next((s for s in db_studies if s.id == missing_study_id), None)
            if study and study.status != StudyStatus.abandoned:
                study.status = StudyStatus.abandoned
                StudyService.add_study_update_event(study,
                                                    status=StudyStatus.abandoned,
                                                    event_type=StudyEventType.automatic)

    def sync_with_protocol_builder_if_enabled(self, user, specs):
        """Assures that the studies we have locally for the given user are
        in sync with the studies available in protocol builder. """

        if ProtocolBuilderService.is_enabled():

            app.logger.info("The Protocol Builder is enabled. app.config['PB_ENABLED'] = " +
                            str(app.config['PB_ENABLED']))

            # Get studies matching this user from Protocol Builder
            if user:
                pb_studies: List[ProtocolBuilderCreatorStudy] = (
                    ProtocolBuilderService.get_studies(user.uid))
            else:
                pb_studies = []

            # Get studies from the database
            db_studies = session.query(StudyModel).filter_by(user_uid=user.uid).all()

            # Update all studies from the protocol builder, create new studies as needed.
            # Further assures that every active study (that does exist in the protocol builder)
            # has a reference to every available workflow (though some may not have started yet)
            self.__process_pb_studies(pb_studies, db_studies, user, specs)

            # Process studies in the DB that are no longer in Protocol Builder
            missing_studies, exempt_studies = \
                self.__get_missing_and_exempt_studies(db_studies, pb_studies)
            self.__delete_exempt_studies(exempt_studies)
            self.__abandon_missing_studies(missing_studies, db_studies)

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
        if status.get(cat.id):
            cat_meta.id = cat.id
            cat_meta.state = WorkflowState[status.get(cat.id)['status']].value
            if 'message' in status.get(cat.id):
                cat_meta.message = status.get(cat.id)['message']
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
                                       last_updated=datetime.now(timezone.utc))
        session.add(workflow_model)
        session.commit()
        return workflow_model

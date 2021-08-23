import urllib
from copy import copy
from datetime import datetime
from typing import List

import flask
import requests
from SpiffWorkflow import WorkflowException
from SpiffWorkflow.bpmn.PythonScriptEngine import Box
from SpiffWorkflow.exceptions import WorkflowTaskExecException
from ldap3.core.exceptions import LDAPSocketOpenError

from crc import db, session, app
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel
from crc.models.email import EmailModel
from crc.models.file import FileModel, File
from crc.models.ldap import LdapSchema

from crc.models.protocol_builder import ProtocolBuilderStudy, ProtocolBuilderStatus
from crc.models.study import StudyModel, Study, StudyStatus, Category, WorkflowMetadata, StudyEventType, StudyEvent, \
    IrbStatus, StudyAssociated, StudyAssociatedSchema
from crc.models.task_event import TaskEventModel, TaskEvent
from crc.models.workflow import WorkflowSpecCategoryModel, WorkflowModel, WorkflowSpecModel, WorkflowState, \
    WorkflowStatus, WorkflowSpecDependencyFile
from crc.services.document_service import DocumentService
from crc.services.file_service import FileService
from crc.services.ldap_service import LdapService
from crc.services.lookup_service import LookupService
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.workflow_processor import WorkflowProcessor


class StudyService(object):
    """Provides common tools for working with a Study"""
    INVESTIGATOR_LIST = "investigators.xlsx"  # A reference document containing details about what investigators to show, and when.

    @staticmethod
    def _is_valid_study(study_id):
        study_info = ProtocolBuilderService().get_study_details(study_id)
        if 'REVIEW_TYPE' in study_info.keys() and study_info['REVIEW_TYPE'] in [2, 3, 23, 24]:
            return True
        return False

    def get_studies_for_user(self, user, include_invalid=False):
        """Returns a list of all studies for the given user."""
        associated = session.query(StudyAssociated).filter_by(uid=user.uid, access=True).all()
        associated_studies = [x.study_id for x in associated]
        db_studies = session.query(StudyModel).filter((StudyModel.user_uid == user.uid) |
                                                      (StudyModel.id.in_(associated_studies))).all()

        studies = []
        for study_model in db_studies:
            if include_invalid or self._is_valid_study(study_model.id):
                studies.append(StudyService.get_study(study_model.id, study_model, do_status=False))
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
    def get_study(study_id, study_model: StudyModel = None, do_status=False):
        """Returns a study model that contains all the workflows organized by category.
        IMPORTANT:  This is intended to be a lightweight call, it should never involve
        loading up and executing all the workflows in a study to calculate information."""
        if not study_model:
            study_model = session.query(StudyModel).filter_by(id=study_id).first()

        study = Study.from_model(study_model)
        study.create_user_display = LdapService.user_info(study.user_uid).display_name
        last_event: TaskEventModel = session.query(TaskEventModel) \
            .filter_by(study_id=study_id, action='COMPLETE') \
            .order_by(TaskEventModel.date.desc()).first()
        if last_event is None:
            study.last_activity_user = 'Not Started'
            study.last_activity_date = ""
        else:
            study.last_activity_user = LdapService.user_info(last_event.user_uid).display_name
            study.last_activity_date = last_event.date
        study.categories = StudyService.get_categories()
        workflow_metas = StudyService._get_workflow_metas(study_id)
        files = FileService.get_files_for_study(study.id)
        files = (File.from_models(model, FileService.get_file_data(model.id),
                                  DocumentService.get_dictionary()) for model in files)
        study.files = list(files)
        # Calling this line repeatedly is very very slow.  It creates the
        # master spec and runs it.  Don't execute this for Abandoned studies, as
        # we don't have the information to process them.
        if study.status != StudyStatus.abandoned:
            # this line is taking 99% of the time that is used in get_study.
            # see ticket #196
            if do_status:
                # __get_study_status() runs the master workflow to generate the status dictionary
                status = StudyService._get_study_status(study_model)
                study.warnings = StudyService._update_status_of_workflow_meta(workflow_metas, status)

            # Group the workflows into their categories.
            for category in study.categories:
                category.workflows = {w for w in workflow_metas if w.category_id == category.id}

        return study

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
        owner = StudyAssociated(uid=study.user_uid, role='owner', send_email=True, access=True)
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
        db.session.query(StudyAssociated).filter((StudyAssociated.study_id == study_id) & (StudyAssociated.uid ==
                                                                                           uid)).delete()

        newAssociate = StudyAssociated()
        newAssociate.study_id = study_id
        newAssociate.uid = uid
        newAssociate.role = role
        newAssociate.send_email = send_email
        newAssociate.access = access
        session.add(newAssociate)
        session.commit()
        return True

    @staticmethod
    def delete_study(study_id):
        session.query(TaskEventModel).filter_by(study_id=study_id).delete()
        session.query(StudyAssociated).filter_by(study_id=study_id).delete()
        session.query(EmailModel).filter_by(study_id=study_id).delete()
        session.query(StudyEvent).filter_by(study_id=study_id).delete()

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
        session.query(WorkflowSpecDependencyFile).filter_by(workflow_id=workflow_id).delete(synchronize_session='fetch')
        session.query(FileModel).filter_by(workflow_id=workflow_id).update({'archived': True, 'workflow_id': None})

        session.delete(workflow)
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
        doc_dictionary = DocumentService.get_dictionary()

        documents = {}
        for code, doc in doc_dictionary.items():

            doc['required'] = False
            if ProtocolBuilderService.is_enabled() and doc['id']:
                pb_data = next((item for item in pb_docs if int(item['AUXDOCID']) == int(doc['id'])), None)
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
            doc_files = FileService.get_files_for_study(study_id=study_id, irb_doc_code=code)
            doc['count'] = len(doc_files)
            doc['files'] = []

            # when we run tests - it doesn't look like the user is available
            # so we return a bogus token
            token = 'not_available'
            if hasattr(flask.g, 'user'):
                token = flask.g.user.encode_auth_token()
            for file in doc_files:
                file_data = {'file_id': file.id,
                             'name': file.name,
                             'url': app.config['APPLICATION_ROOT'] +
                                    'file/' + str(file.id) +
                                    '/download?auth_token=' +
                                    urllib.parse.quote_plus(token),
                             'workflow_id': file.workflow_id
                             }
                data = db.session.query(DataStoreModel).filter(DataStoreModel.file_id == file.id).all()
                data_store_data = {}
                for d in data:
                    data_store_data[d.key] = d.value
                file_data["data_store"] = data_store_data
                doc['files'].append(Box(file_data))
                # update the document status to match the status of the workflow it is in.
                if 'status' not in doc or doc['status'] is None:
                    workflow: WorkflowModel = session.query(WorkflowModel).filter_by(id=file.workflow_id).first()
                    doc['status'] = workflow.status.value

            documents[code] = doc
        return Box(documents)

    @staticmethod
    def get_investigator_dictionary():
        """Returns a dictionary of document details keyed on the doc_code."""
        file_data = FileService.get_reference_file_data(StudyService.INVESTIGATOR_LIST)
        lookup_model = LookupService.get_lookup_model_for_file_data(file_data, 'code', 'label')
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
            # Further assures that every active study (that does exist in the protocol builder)
            # has a reference to every available workflow (though some may not have started yet)
            for pb_study in pb_studies:
                new_status = None
                db_study = next((s for s in db_studies if s.id == pb_study.STUDYID), None)
                if not db_study:
                    db_study = StudyModel(id=pb_study.STUDYID)
                    db_study.status = None  # Force a new sa
                    new_status = StudyStatus.in_progress
                    session.add(db_study)
                    db_studies.append(db_study)

                db_study.update_from_protocol_builder(pb_study)
                StudyService._add_all_workflow_specs_to_study(db_study)

                # If there is a new automatic status change and there isn't a manual change in place, record it.
                if new_status and db_study.status != StudyStatus.hold:
                    db_study.status = new_status
                    StudyService.add_study_update_event(db_study,
                                                        status=new_status,
                                                        event_type=StudyEventType.automatic)

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
    def _update_status_of_workflow_meta(workflow_metas, status):
        # Update the status on each workflow
        warnings = []
        for wfm in workflow_metas:
            wfm.state_message = ''
            # do we have a status for you
            if wfm.name not in status.keys():
                warnings.append(ApiError("missing_status", "No status specified for workflow %s" % wfm.name))
                continue
            if not isinstance(status[wfm.name], dict):
                warnings.append(ApiError(code='invalid_status',
                                         message=f'Status must be a dictionary with "status" and "message" keys. Name is {wfm.name}. Status is {status[wfm.name]}'))
                continue
            if 'status' not in status[wfm.name].keys():
                warnings.append(ApiError("missing_status",
                                         "Workflow '%s' does not have a status setting" % wfm.name))
                continue
            if not WorkflowState.has_value(status[wfm.name]['status']):
                warnings.append(ApiError("invalid_state",
                                         "Workflow '%s' can not be set to '%s', should be one of %s" % (
                                             wfm.name, status[wfm.name]['status'], ",".join(WorkflowState.list())
                                         )))
                continue
            wfm.state = WorkflowState[status[wfm.name]['status']]
            if 'message' in status[wfm.name].keys():
                wfm.state_message = status[wfm.name]['message']
        return warnings

    @staticmethod
    def _get_workflow_metas(study_id):
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
    def _get_study_status(study_model):
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
    def _add_all_workflow_specs_to_study(study_model: StudyModel):
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
                                       user_id=None,
                                       workflow_spec_id=spec.id,
                                       last_updated=datetime.utcnow())
        session.add(workflow_model)
        session.commit()
        return workflow_model

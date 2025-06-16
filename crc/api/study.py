import json
from datetime import datetime, timezone

from flask import g, send_file
from sqlalchemy.exc import IntegrityError
from crc import app, session
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.study import Study, StudyEventType, StudyModel, StudySchema, StudyForUpdateSchema, \
    StudyStatus, StudyAssociatedSchema, ProgressStatus, Category
from crc.models.task_log import TaskLogQuery, TaskLogQuerySchema
from crc.services.spreadsheet_service import SpreadsheetService
from crc.services.study_service import StudyService
from crc.services.task_logging_service import TaskLoggingService
from crc.services.user_service import UserService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from crc.services.workflow_spec_service import WorkflowSpecService
from crc.api.user import verify_token

import io


def add_study(body):
    # fixme: Remove this method.  We don't add a study this way except in testing.
    """
    This method seems to be used by one test, and no where else!
    Or any study like object. Body should include a title, and primary_investigator_id """
    """Or any study like object. Body should include a title """
    if 'title' not in body:
        raise ApiError("missing_title", "Can't create a new study without a title.")

    study_model = StudyModel(user_uid=UserService.current_user().uid,
                             title=body['title'],
                             last_updated=datetime.now(timezone.utc),
                             status=StudyStatus.in_progress,
                             review_type=body['review_type'])
    session.add(study_model)
    StudyService.add_study_update_event(study_model,
                                        status=StudyStatus.in_progress,
                                        event_type=StudyEventType.user,
                                        user_uid=g.user.uid)

    spec_service = WorkflowSpecService()
    specs = spec_service.get_specs()
    categories = spec_service.get_categories()
    errors = StudyService.add_all_workflow_specs_to_study(study_model, specs)
    session.commit()

    master_workflow_results = __run_master_spec(study_model, spec_service.master_spec)
    study = StudyService().get_study(study_model.id, categories, master_workflow_results=master_workflow_results,
                                     process_categories=True)
    study_data = StudySchema().dump(study)
    study_data["errors"] = ApiErrorSchema(many=True).dump(errors)
    return study_data


def __run_master_spec(study_model, master_spec):
    """Runs the master workflow spec to get details on the status of each workflow.
       This is a fairly expensive call."""
    """Uses the Top Level Workflow to calculate the status of the study, and its
    workflow models."""
    if not master_spec:
        raise ApiError("missing_master_spec", "No specifications are currently marked as the master spec.")
    return WorkflowProcessor.run_master_spec(master_spec, study_model)


def update_study(study_id, body):
    spec_service = WorkflowSpecService()
    categories = spec_service.get_categories()

    """Pretty limited, but allows manual modifications to the study status """
    if study_id is None:
        raise ApiError('unknown_study', 'Please provide a valid Study ID.')

    study_model = session.query(StudyModel).filter_by(id=study_id).first()
    if study_model is None:
        raise ApiError('unknown_study', 'The study "' + study_id + '" is not recognized.')

    study: Study = StudyForUpdateSchema().load(body)

    status = StudyStatus(study.status)
    study_model.last_updated = datetime.now(timezone.utc)

    if study_model.status != status:
        study_model.status = status
        StudyService.add_study_update_event(study_model, status, StudyEventType.user,
                                            user_uid=UserService.current_user().uid if UserService.has_user() else None,
                                            comment='' if not hasattr(study, 'comment') else study.comment,
                                            )

    if status == StudyStatus.open_for_enrollment:
        study_model.enrollment_date = study.enrollment_date
        study_model.progress_status = ProgressStatus.finance_in_progress

    session.add(study_model)
    session.commit()

    if status == StudyStatus.abandoned or status == StudyStatus.hold:
        WorkflowService.process_workflows_for_cancels(study_id)

    # Need to reload the full study to return it to the frontend
    study = StudyService.get_study(study_id, categories)
    return StudySchema().dump(study)


def get_study(study_id, update_status=False):
    spec_service = WorkflowSpecService()
    categories = spec_service.get_categories()
    master_workflow_results = {}
    if update_status:
        study_model = session.query(StudyModel).filter(StudyModel.id == study_id).first()
        master_workflow_results = __run_master_spec(study_model, spec_service.master_spec)
        WorkflowService().update_workflow_state_from_master_workflow(study_id, master_workflow_results)
    study = StudyService().get_study(study_id, categories, master_workflow_results=master_workflow_results, process_categories=True)
    if study is None:
        raise ApiError("unknown_study",  'The study "' + study_id + '" is not recognized.', status_code=404)
    return StudySchema().dump(study)


def get_study_associates(study_id):
    return StudyAssociatedSchema(many=True).dump(StudyService.get_study_associates(study_id))


def get_logs_for_study(study_id, body):
    task_log_query = TaskLogQuery(**body)
    task_log_query.study_id = study_id  # Force the study id
    return TaskLogQuerySchema().dump(
        TaskLoggingService.get_logs_for_study_paginated(study_id, task_log_query))


def download_logs_for_study(study_id, auth_token):
    # Download links incorporate an auth token in the request for direct download
    if not verify_token(auth_token):
        raise ApiError('not_authenticated', 'You need to include an authorization token in the URL with this')

    title = f'Study {study_id}'
    logs, headers = TaskLoggingService.get_log_data_for_download(study_id)
    spreadsheet = SpreadsheetService.create_spreadsheet(logs, headers, title)

    return send_file(
        io.BytesIO(spreadsheet),
        download_name='logs.xlsx',
        mimetype='xlsx',
        max_age=-1,  # Don't cache these files on the browser.
        last_modified=datetime.now(),
        as_attachment=True
    )


def delete_study(study_id):
    try:
        StudyService.delete_study(study_id)
    except IntegrityError as ie:
        session.rollback()
        message = "Failed to delete Study #%i due to an Integrity Error: %s" % (study_id, str(ie))
        raise ApiError(code="study_integrity_error", message=message)


def user_studies():
    """Returns all the studies associated with the current user. """
    app.logger.info("Getting user studies")
    user = UserService.current_user(allow_admin_impersonate=True)
    spec_service = WorkflowSpecService()
    specs = spec_service.get_specs()
    cats = spec_service.get_categories()
    StudyService().sync_with_protocol_builder_if_enabled(user, specs)
    studies = StudyService().get_studies_for_user(user, categories=cats)


    # Disable this check - we don't want to raise this error.
    # if len(studies) == 0:
    #     studies = StudyService().get_studies_for_user(user, categories=cats, include_invalid=True)
    #     if len(studies) > 0:
    #         message = f"All studies associated with User: {user.uid} failed study validation"
    #         raise ApiError(code="study_integrity_error", message=message)

    results = StudySchema(many=True).dump(studies)
    return results


def all_studies():
    """Returns all studies (regardless of user) with submitted files"""
    studies = StudyService.get_all_studies_with_files()
    results = StudySchema(many=True).dump(studies)
    return results

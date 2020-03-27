from typing import List

from SpiffWorkflow.exceptions import WorkflowException
from connexion import NoContent
from flask import g
from sqlalchemy.exc import IntegrityError

from crc import session, app
from crc.api.common import ApiError, ApiErrorSchema
from crc.api.workflow import __get_workflow_api_model
from crc.models.api_models import WorkflowApiSchema
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudy
from crc.models.study import StudyModelSchema, StudyModel
from crc.models.workflow import WorkflowModel, WorkflowSpecModel
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.workflow_processor import WorkflowProcessor


def add_study(body):
    study: StudyModel = StudyModelSchema().load(body, session=session)
    session.add(study)
    errors = add_all_workflow_specs_to_study(study)
    session.commit()
    study_data = StudyModelSchema().dump(study)
    study_data["errors"] = ApiErrorSchema(many=True).dump(errors)
    return study_data


def update_study(study_id, body):
    if study_id is None:
        raise ApiError('unknown_study', 'Please provide a valid Study ID.')

    study = session.query(StudyModel).filter_by(id=study_id).first()

    if study is None:
        raise ApiError('unknown_study', 'The study "' + study_id + '" is not recognized.')

    schema = StudyModelSchema()
    study = schema.load(body, session=session, instance=study, partial=True)
    session.add(study)
    session.commit()
    return schema.dump(study)


def get_study(study_id):
    study = session.query(StudyModel).filter_by(id=study_id).first()
    schema = StudyModelSchema()
    if study is None:
        return NoContent, 404
    return schema.dump(study)


def delete_study(study_id):
    try:
        session.query(StudyModel).filter_by(id=study_id).delete()
    except IntegrityError as ie:
        session.rollback()
        app.logger.error("Failed to delete Study #%i due to an Integrity Error: %s" % (study_id, str(ie)))
        raise ApiError(code="study_integrity_error", message="This study contains running workflows that is "
                                                             "preventing deletion.  Please delete the workflows " +
                                                             "before proceeding.")


def all_studies():
    """Returns all the studies associated with the current user.  Assures we are
    in sync with values read in from the protocol builder. """

    """:type: crc.models.user.UserModel"""

    # Get studies matching this user from Protocol Builder
    pb_studies: List[ProtocolBuilderStudy] = ProtocolBuilderService.get_studies(g.user.id)

    # Get studies from the database
    db_studies = session.query(StudyModel).filter_by(user_uid=g.user.uid).all()

    # Update all studies from the protocol builder, create new studies as needed.
    for pb_study in pb_studies:
        db_study = next((s for s in db_studies if s.id == pb_study.STUDYID), None)
        if not db_study:
            db_study = StudyModel(id=pb_study.STUDYID)
            session.add(db_study)
            db_studies.append(db_study)
        db_study.update_from_protocol_builder(pb_study)

    # Mark studies as inactive that are no longer in Protocol Builder
    for study in db_studies:
        pb_study = next((pbs for pbs in pb_studies if pbs.STUDYID == study.id), None)
        if not pb_study:
            study.inactive = True
            study.protocol_builder_status = ProtocolBuilderStatus.INACTIVE

    session.commit()
    # Return updated studies
    results = StudyModelSchema(many=True).dump(db_studies)
    return results


def post_update_study_from_protocol_builder(study_id):
    """Update a single study based on data received from
    the protocol builder."""

    db_study = session.query(StudyModel).filter_by(study_id=study_id).all()
    pb_studies: List[ProtocolBuilderStudy] = ProtocolBuilderService.get_studies(g.user.id)
    pb_study = next((pbs for pbs in pb_studies if pbs.STUDYID == study_id), None)
    if pb_study:
        db_study.update_from_protocol_builder(pb_study)
    else:
        db_study.inactive = True
        db_study.protocol_builder_status = ProtocolBuilderStatus.INACTIVE

    return NoContent, 304


def get_study_workflows(study_id):
    """Returns all the workflows related to this study"""
    workflow_models = session.query(WorkflowModel).filter_by(study_id=study_id).all()
    api_models = []
    for workflow_model in workflow_models:
        processor = WorkflowProcessor(workflow_model,
                                      workflow_model.bpmn_workflow_json)
        api_models.append(__get_workflow_api_model(processor))
    schema = WorkflowApiSchema(many=True)
    return schema.dump(api_models)


def add_all_workflow_specs_to_study(study):
    existing_models = session.query(WorkflowModel).filter(WorkflowModel.study_id == study.id).all()
    existing_specs = list(m.workflow_spec_id for m in existing_models)
    new_specs = session.query(WorkflowSpecModel). \
        filter(WorkflowSpecModel.is_master_spec == False). \
        filter(WorkflowSpecModel.id.notin_(existing_specs)). \
        all()
    errors = []
    for workflow_spec in new_specs:
        try:
            WorkflowProcessor.create(study.id, workflow_spec.id)
        except WorkflowException as we:
            errors.append(ApiError.from_task_spec("workflow_execution_exception", str(we), we.sender))
    return errors

def add_workflow_to_study(study_id, body):
    workflow_spec_model: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=body["id"]).first()
    if workflow_spec_model is None:
        raise ApiError('unknown_spec', 'The specification "' + body['id'] + '" is not recognized.')
    processor = WorkflowProcessor.create(study_id, workflow_spec_model.id)
    return WorkflowApiSchema().dump(__get_workflow_api_model(processor))

import logging
from typing import List, Optional, Union, Tuple, Dict

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
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.protocol_builder import ProtocolBuilderService


def all_studies():
    return update_from_protocol_builder()


def add_study(body):
    study: StudyModel = StudyModelSchema().load(body, session=session)
    status_spec = __get_status_spec(study.status_spec_id)

    # Get latest status spec version
    if status_spec is not None:
        study.status_spec_id = status_spec.id
        study.status_spec_version = WorkflowProcessor.get_latest_version_string(status_spec.id)

    session.add(study)
    session.commit()

    __add_study_workflows_from_status(study.id, status_spec)
    return StudyModelSchema().dump(study)


def __get_status_spec(status_spec_id):
    if status_spec_id is None:
        return session.query(WorkflowSpecModel).filter_by(is_status=True).first()
    else:
        return session.query(WorkflowSpecModel).filter_by(id=status_spec_id).first()


def __add_study_workflows_from_status(study_id, status_spec):
    all_specs = session.query(WorkflowSpecModel).all()
    if status_spec is not None:
        # Run status spec to get list of workflow specs applicable to this study
        status_processor = WorkflowProcessor.create(study_id, status_spec)
        status_processor.do_engine_steps()
        status_data = status_processor.next_task().data

        # Only add workflow specs listed in status spec
        for spec in all_specs:
            if spec.id in status_data and status_data[spec.id]:
                WorkflowProcessor.create(study_id, spec.id)
    else:
        # No status spec. Just add all workflows.
        for spec in all_specs:
            WorkflowProcessor.create(study_id, spec.id)


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

def update_from_protocol_builder():
    """Updates the list of known studies for a given user based on data received from
    the protocol builder."""

    user = g.user
    """:type: crc.models.user.UserModel"""

    # Get studies matching this user from Protocol Builder
    pb_studies: List[ProtocolBuilderStudy] = get_user_pb_studies()

    # Get studies from the database
    db_studies = session.query(StudyModel).filter_by(user_uid=user.uid).all()
    db_study_ids = list(map(lambda s: s.id, db_studies))
    pb_study_ids = list(map(lambda s: s['STUDYID'], pb_studies))

    for pb_study in pb_studies:

        # Update studies with latest data from Protocol Builder
        if pb_study['STUDYID'] in db_study_ids:
            update_study(pb_study['STUDYID'], map_pb_study_to_study(pb_study))

        # Add studies from Protocol Builder that aren't in the database yet
        else:
            new_study = map_pb_study_to_study(pb_study)
            add_study(new_study)

    # Mark studies as inactive that are no longer in Protocol Builder
    for study_id in db_study_ids:
        if study_id not in pb_study_ids:
            update_study(
                study_id=study_id,
                body={
                    'inactive': True,
                    'protocol_builder_status': ProtocolBuilderStatus.INACTIVE.name
                }
            )

    # Return updated studies
    updated_studies = session.query(StudyModel).filter_by(user_uid=user.uid).all()
    results = StudyModelSchema(many=True).dump(updated_studies)
    return results


def post_update_study_from_protocol_builder(study_id):
    """Update a single study based on data received from
    the protocol builder."""

    pb_studies: List[ProtocolBuilderStudy] = get_user_pb_studies()
    for pb_study in pb_studies:
        if pb_study['STUDYID'] == study_id:
            return update_study(study_id, map_pb_study_to_study(pb_study))

    return NoContent, 304


def get_study_workflows(study_id):

    # Get study
    study: StudyModel = session.query(StudyModel).filter_by(id=study_id).first()

    # Get study status spec
    status_spec: WorkflowSpecModel = session.query(WorkflowSpecModel)\
        .filter_by(is_status=True)\
        .filter_by(id=study.status_spec_id)\
        .first()

    status_data = None

    if status_spec is not None:
        # Run status spec
        status_workflow_model: WorkflowModel = session.query(WorkflowModel)\
            .filter_by(study_id=study.id)\
            .filter_by(workflow_spec_id=status_spec.id)\
            .first()
        status_processor = WorkflowProcessor(status_workflow_model)

        # Get list of active workflow specs for study
        status_processor.do_engine_steps()
        status_data = status_processor.bpmn_workflow.last_task.data

        # Get study workflows
        workflow_models = session.query(WorkflowModel)\
            .filter_by(study_id=study_id)\
            .filter(WorkflowModel.workflow_spec_id != status_spec.id)\
            .all()
    else:
        # Get study workflows
        workflow_models = session.query(WorkflowModel)\
            .filter_by(study_id=study_id)\
            .all()
    api_models = []
    for workflow_model in workflow_models:
        processor = WorkflowProcessor(workflow_model,
                                      workflow_model.bpmn_workflow_json)
        api_models.append(__get_workflow_api_model(processor, status_data))
    schema = WorkflowApiSchema(many=True)
    return schema.dump(api_models)


def add_workflow_to_study(study_id, body):
    workflow_spec_model: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=body["id"]).first()
    if workflow_spec_model is None:
        raise ApiError('unknown_spec', 'The specification "' + body['id'] + '" is not recognized.')
    processor = WorkflowProcessor.create(study_id, workflow_spec_model.id)

    # If workflow spec is a status spec, update the study status spec
    if workflow_spec_model.is_status:
        study = session.query(StudyModel).filter_by(id=study_id).first()
        study.status_spec_id = workflow_spec_model.id
        study.status_spec_version = processor.get_spec_version()
        session.add(study)
        session.commit()

    return WorkflowApiSchema().dump(__get_workflow_api_model(processor))


def get_user_pb_studies() -> List[ProtocolBuilderStudy]:
    """Get studies from Protocol Builder matching the given user"""

    user = g.user
    """:type: crc.models.user.UserModel"""

    return ProtocolBuilderService.get_studies(user.uid)


def map_pb_study_to_study(pb_study):
    """Translates the given dict of ProtocolBuilderStudy properties to dict of StudyModel attributes"""
    prop_map = {
        'STUDYID': 'id',
        'HSRNUMBER': 'hsr_number',
        'TITLE': 'title',
        'NETBADGEID': 'user_uid',
        'DATE_MODIFIED': 'last_updated',
    }
    study_info = {}

    # Translate Protocol Builder property names to Study attributes
    for k, v in pb_study.items():
        if k in prop_map:
            study_info[prop_map[k]] = v

    # Translate Protocol Builder states to enum values
    status = ProtocolBuilderStatus.DRAFT
    pb_details = ProtocolBuilderService.get_study_details(pb_study['STUDYID'])

    if 'Q_COMPLETE' in pb_study and pb_study['Q_COMPLETE']:
        if 'UPLOAD_COMPLETE' in pb_details and pb_details['UPLOAD_COMPLETE']:
            if 'HSRNUMBER' in pb_study and pb_study['HSRNUMBER']:
                status = ProtocolBuilderStatus.REVIEW_COMPLETE
            else:
                status = ProtocolBuilderStatus.IN_REVIEW
        else:
            status = ProtocolBuilderStatus.IN_PROCESS

    study_info['protocol_builder_status'] = status.name
    study_info['inactive'] = False
    return study_info



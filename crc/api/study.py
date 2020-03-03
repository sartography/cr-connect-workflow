from typing import List, Optional, Union, Tuple, Dict

from connexion import NoContent
from flask import g

from crc import session, auth
from crc.api.common import ApiError, ApiErrorSchema
from crc.api.workflow import __get_workflow_api_model
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudy
from crc.models.study import StudyModelSchema, StudyModel
from crc.models.workflow import WorkflowModel, WorkflowApiSchema, WorkflowSpecModel, WorkflowApi
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.protocol_builder import ProtocolBuilderService


@auth.login_required
def all_studies():
    return update_from_protocol_builder()


@auth.login_required
def add_study(body):
    study = StudyModelSchema().load(body, session=session)
    session.add(study)
    session.commit()

    # FIXME: We need to ask the protocol builder what workflows to add to the study, not just add them all.
    for spec in session.query(WorkflowSpecModel).all():
        WorkflowProcessor.create(study.id, spec.id)
    return StudyModelSchema().dump(study)


@auth.login_required
def update_study(study_id, body):
    if study_id is None:
        error = ApiError('unknown_study', 'Please provide a valid Study ID.')
        return ApiErrorSchema.dump(error), 404

    study = session.query(StudyModel).filter_by(id=study_id).first()

    if study is None:
        error = ApiError('unknown_study', 'The study "' + study_id + '" is not recognized.')
        return ApiErrorSchema.dump(error), 404

    schema = StudyModelSchema()
    study = schema.load(body, session=session, instance=study, partial=True)
    session.add(study)
    session.commit()
    return schema.dump(study)


@auth.login_required
def get_study(study_id):
    study = session.query(StudyModel).filter_by(id=study_id).first()
    schema = StudyModelSchema()
    if study is None:
        return NoContent, 404
    return schema.dump(study)


@auth.login_required
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
                    'protocol_builder_status': ProtocolBuilderStatus.INACTIVE._value_
                }
            )

    # Return updated studies
    updated_studies = session.query(StudyModel).filter_by(user_uid=user.uid).all()
    results = StudyModelSchema(many=True).dump(updated_studies)
    return results


@auth.login_required
def post_update_study_from_protocol_builder(study_id):
    """Update a single study based on data received from
    the protocol builder."""

    pb_studies: List[ProtocolBuilderStudy] = get_user_pb_studies()
    for pb_study in pb_studies:
        if pb_study['STUDYID'] == study_id:
            return update_study(study_id, map_pb_study_to_study(pb_study))

    return NoContent, 304


@auth.login_required
def get_study_workflows(study_id):
    workflow_models = session.query(WorkflowModel).filter_by(study_id=study_id).all()
    api_models = []
    for workflow_model in workflow_models:
        processor = WorkflowProcessor(workflow_model.workflow_spec_id,
                                      workflow_model.bpmn_workflow_json)
        api_models.append(__get_workflow_api_model(processor))
    schema = WorkflowApiSchema(many=True)
    return schema.dump(api_models)


@auth.login_required
def add_workflow_to_study(study_id, body):
    workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id=body["id"]).first()
    if workflow_spec_model is None:
        error = ApiError('unknown_spec', 'The specification "' + body['id'] + '" is not recognized.')
        return ApiErrorSchema.dump(error), 404
    processor = WorkflowProcessor.create(study_id, workflow_spec_model.id)
    return WorkflowApiSchema().dump(__get_workflow_api_model(processor))


@auth.login_required
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
    if pb_study['Q_COMPLETE']:
        if pb_study['UPLOAD_COMPLETE']:
            if pb_study['HSRNUMBER']:
                status = ProtocolBuilderStatus.REVIEW_COMPLETE
            else:
                status = ProtocolBuilderStatus.IN_REVIEW
        else:
            status = ProtocolBuilderStatus.IN_PROCESS

    study_info['protocol_builder_status'] = status._value_
    study_info['inactive'] = False
    return study_info


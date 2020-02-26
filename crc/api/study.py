from typing import List

from dateutil.parser import parse
from connexion import NoContent
from flask import g

from crc import session, auth
from crc.api.common import ApiError, ApiErrorSchema
from crc.api.workflow import __get_workflow_api_model
from crc.models.study import StudyModelSchema, StudyModel, ProtocolBuilderStudy, ProtocolBuilderStatus
from crc.models.workflow import WorkflowModel, WorkflowApiSchema, WorkflowSpecModel
from crc.services import protocol_builder
from crc.services.workflow_processor import WorkflowProcessor


@auth.login_required
def all_studies():
    user = g.user
    """:type: crc.models.user.UserModel"""

    # Get studies matching this user from Protocol Builder
    pb_studies: List[ProtocolBuilderStudy] = protocol_builder.get_studies(user.uid)

    schema = StudyModelSchema(many=True)
    db_studies = session.query(StudyModel).filter_by(user_uid=user.uid).all()
    db_study_ids = list(map(lambda s: s.id, db_studies))

    for pb_study in pb_studies:
        if pb_study['HSRNUMBER'] not in db_study_ids:
            status = ProtocolBuilderStatus.complete._value_ if pb_study['Q_COMPLETE'] else ProtocolBuilderStatus.in_process._value_
            add_study({
                'id': pb_study['HSRNUMBER'],
                'title': pb_study['TITLE'],
                'protocol_builder_status': status,
                'user_uid': pb_study['NETBADGEID'],
                'last_updated': pb_study['DATE_MODIFIED']
            })

    db_studies = session.query(StudyModel).filter_by(user_uid=user.uid).all()
    return schema.dump(db_studies)


def add_study(body):
    study = StudyModelSchema().load(body, session=session)
    session.add(study)
    session.commit()
    # FIXME: We need to ask the protocol builder what workflows to add to the study, not just add them all.
    for spec in session.query(WorkflowSpecModel).all():
        WorkflowProcessor.create(study.id, spec.id)
    return StudyModelSchema().dump(study)


def update_study(study_id, body):
    if study_id is None:
        error = ApiError('unknown_study', 'Please provide a valid Study ID.')
        return ApiErrorSchema.dump(error), 404

    study = session.query(StudyModel).filter_by(id=study_id).first()

    if study is None:
        error = ApiError('unknown_study', 'The study "' + study_id + '" is not recognized.')
        return ApiErrorSchema.dump(error), 404

    study = StudyModelSchema().load(body, session=session, instance=study)
    session.add(study)
    session.commit()
    return StudyModelSchema().dump(study)


def get_study(study_id):
    study = session.query(StudyModel).filter_by(id=study_id).first()
    schema = StudyModelSchema()
    if study is None:
        return NoContent, 404
    return schema.dump(study)


def update_from_protocol_builder():
    """Call the """


def post_update_study_from_protocol_builder(study_id):
    """This will update the list of known studies based on data received from
    the protocol builder."""

    # todo: Actually get data from an external service here
    return NoContent, 304


def get_study_workflows(study_id):
    workflow_models = session.query(WorkflowModel).filter_by(study_id=study_id).all()
    api_models = []
    for workflow_model in workflow_models:
        processor = WorkflowProcessor(workflow_model.workflow_spec_id,
                                      workflow_model.bpmn_workflow_json)
        api_models.append(__get_workflow_api_model(processor))
    schema = WorkflowApiSchema(many=True)
    return schema.dump(api_models)


def add_workflow_to_study(study_id, body):
    workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id=body["id"]).first()
    if workflow_spec_model is None:
        error = ApiError('unknown_spec', 'The specification "' + body['id'] + '" is not recognized.')
        return ApiErrorSchema.dump(error), 404
    processor = WorkflowProcessor.create(study_id, workflow_spec_model.id)
    return WorkflowApiSchema().dump(__get_workflow_api_model(processor))

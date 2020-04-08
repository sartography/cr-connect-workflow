from typing import List

from connexion import NoContent
from flask import g
from sqlalchemy.exc import IntegrityError

from crc import session, app
from crc.api.common import ApiError, ApiErrorSchema
from crc.api.workflow import __get_workflow_api_model
from crc.models.api_models import WorkflowApiSchema
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudy
from crc.models.study import StudySchema, StudyModel, Study
from crc.models.workflow import WorkflowModel, WorkflowSpecModel
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor


def add_study(body):
    """This should never get called, and is subject to deprication.  Studies
    should be added through the protocol builder only."""
    study: Study = StudySchema().load(body)
    study_model = StudyModel(**study.model_args())
    session.add(study_model)
    errors = StudyService._add_all_workflow_specs_to_study(study)
    session.commit()
    study_data = StudySchema().dump(study)
    study_data["errors"] = ApiErrorSchema(many=True).dump(errors)
    return study_data


def update_study(study_id, body):
    if study_id is None:
        raise ApiError('unknown_study', 'Please provide a valid Study ID.')

    study_model = session.query(StudyModel).filter_by(id=study_id).first()
    if study_model is None:
        raise ApiError('unknown_study', 'The study "' + study_id + '" is not recognized.')

    study: Study = StudySchema().load(body)
    study.update_model(study_model)
    session.add(study_model)
    session.commit()
    return StudySchema().dump(study)


def get_study(study_id):
    study_service = StudyService()
    study = study_service.get_study(study_id)
`    if(study is None):
        raise ApiError("Study not found", status_code=404)
    schema = StudySchema()
    return schema.dump(study)


def delete_study(study_id):
    try:
        StudyService.delete_study(study_id)
    except IntegrityError as ie:
        session.rollback()
        message = "Failed to delete Study #%i due to an Integrity Error: %s" % (study_id, str(ie))
        raise ApiError(code="study_integrity_error", message=message)


def all_studies():
    """Returns all the studies associated with the current user.  Assures we are
    in sync with values read in from the protocol builder. """
    StudyService.synch_all_studies_with_protocol_builder(g.user)
    studies = StudyService.get_studies_for_user(g.user)
    results = StudySchema(many=True).dump(studies)
    return results


def post_update_study_from_protocol_builder(study_id):
    """Update a single study based on data received from
    the protocol builder."""

    db_study = session.query(StudyModel).filter_by(study_id=study_id).all()
    pb_studies: List[ProtocolBuilderStudy] = ProtocolBuilderService.get_studies(g.user.uid)
    pb_study = next((pbs for pbs in pb_studies if pbs.STUDYID == study_id), None)
    if pb_study:
        db_study.update_from_protocol_builder(pb_study)
    else:
        db_study.inactive = True
        db_study.protocol_builder_status = ProtocolBuilderStatus.INACTIVE

    return NoContent, 304






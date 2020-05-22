from flask import g
from sqlalchemy.exc import IntegrityError

from crc import session
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.study import StudySchema, StudyModel, Study
from crc.services.study_service import StudyService


def add_study(body):
    """Or any study like object. """
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
    if(study is None):
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
    """Returns all the studies associated with the current user. """
    StudyService.synch_with_protocol_builder_if_enabled(g.user)
    studies = StudyService.get_studies_for_user(g.user)
    results = StudySchema(many=True).dump(studies)
    return results


def all_studies_and_files():
    """Returns all studies with submitted files"""
    studies = StudyService.get_studies_for_user(g.user)
    results = StudySchema(many=True).dump(studies)
    return results






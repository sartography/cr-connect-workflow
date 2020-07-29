from datetime import datetime

from flask import g
from sqlalchemy.exc import IntegrityError

from crc import session
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.protocol_builder import ProtocolBuilderStatus
from crc.models.study import StudySchema, StudyModel, Study
from crc.services.study_service import StudyService
from crc.services.user_service import UserService


def add_study(body):
    """Or any study like object. Body should include a title, and primary_investigator_id """
    if 'primary_investigator_id' not in body:
        raise ApiError("missing_pi", "Can't create a new study without a Primary Investigator.")
    if 'title' not in body:
        raise ApiError("missing_title", "Can't create a new study without a title.")

    study_model = StudyModel(user_uid=UserService.current_user().uid,
                             title=body['title'],
                             primary_investigator_id=body['primary_investigator_id'],
                             last_updated=datetime.now(),
                             protocol_builder_status=ProtocolBuilderStatus.active)

    session.add(study_model)
    errors = StudyService._add_all_workflow_specs_to_study(study_model)
    session.commit()
    study = StudyService().get_study(study_model.id)
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
    study = StudyService.get_study(study_id)
    if (study is None):
        raise ApiError("unknown_study",  'The study "' + study_id + '" is not recognized.', status_code=404)
    return StudySchema().dump(study)


def delete_study(study_id):
    try:
        StudyService.delete_study(study_id)
    except IntegrityError as ie:
        session.rollback()
        message = "Failed to delete Study #%i due to an Integrity Error: %s" % (study_id, str(ie))
        raise ApiError(code="study_integrity_error", message=message)


def user_studies():
    """Returns all the studies associated with the current user. """
    user = UserService.current_user(allow_admin_impersonate=True)
    StudyService.synch_with_protocol_builder_if_enabled(user)
    studies = StudyService.get_studies_for_user(user)
    results = StudySchema(many=True).dump(studies)
    return results


def all_studies():
    """Returns all studies (regardless of user) with submitted files"""
    studies = StudyService.get_all_studies_with_files()
    results = StudySchema(many=True).dump(studies)
    return results

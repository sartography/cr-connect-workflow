import json
from typing import List, Optional

import requests

from crc import app
from crc.api.common import ApiError
from crc.models.protocol_builder import ProtocolBuilderStudy, ProtocolBuilderStudySchema, ProtocolBuilderInvestigator, \
    ProtocolBuilderRequiredDocument, ProtocolBuilderStudyDetails, ProtocolBuilderInvestigatorSchema, \
    ProtocolBuilderRequiredDocumentSchema, ProtocolBuilderStudyDetailsSchema


class ProtocolBuilderService(object):
    STUDY_URL = app.config['PB_USER_STUDIES_URL']
    INVESTIGATOR_URL = app.config['PB_INVESTIGATORS_URL']
    REQUIRED_DOCS_URL = app.config['PB_REQUIRED_DOCS_URL']
    STUDY_DETAILS_URL = app.config['PB_STUDY_DETAILS_URL']

    @staticmethod
    def get_studies(user_id) -> Optional[List[ProtocolBuilderStudy]]:
        if not isinstance(user_id, str):
            raise ApiError("invalid_user_id", "This user id is invalid: " + str(user_id))
        response = requests.get(ProtocolBuilderService.STUDY_URL % user_id)
        if response.ok and response.text:
            pb_studies = ProtocolBuilderStudySchema(many=True).loads(response.text)
            return pb_studies
        else:
            raise ApiError("protocol_builder_error",
                           "Received an invalid response from the protocol builder (status %s): %s" %
                           (response.status_code, response.text))

    @staticmethod
    def get_investigators(study_id) -> Optional[List[ProtocolBuilderInvestigator]]:
        ProtocolBuilderService.check_args(study_id)
        response = requests.get(ProtocolBuilderService.INVESTIGATOR_URL % study_id)
        if response.ok and response.text:
            pb_studies = ProtocolBuilderInvestigatorSchema(many=True).loads(response.text)
            return pb_studies
        else:
            raise ApiError("protocol_builder_error",
                           "Received an invalid response from the protocol builder (status %s): %s" %
                           (response.status_code, response.text))

    @staticmethod
    def get_required_docs(study_id) -> Optional[List[ProtocolBuilderRequiredDocument]]:
        ProtocolBuilderService.check_args(study_id)
        response = requests.get(ProtocolBuilderService.REQUIRED_DOCS_URL % study_id)
        if response.ok and response.text:
            pb_studies = ProtocolBuilderRequiredDocumentSchema(many=True).loads(response.text)
            return pb_studies
        else:
            raise ApiError("protocol_builder_error",
                           "Received an invalid response from the protocol builder (status %s): %s" %
                           (response.status_code, response.text))

    @staticmethod
    def get_study_details(study_id) -> Optional[ProtocolBuilderStudyDetails]:
        ProtocolBuilderService.check_args(study_id)
        response = requests.get(ProtocolBuilderService.STUDY_DETAILS_URL % study_id)
        if response.ok and response.text:
            pb_study_details = ProtocolBuilderStudyDetailsSchema().loads(response.text)
            return pb_study_details
        else:
            raise ApiError("protocol_builder_error",
                           "Received an invalid response from the protocol builder (status %s): %s" %
                           (response.status_code, response.text))

    @staticmethod
    def check_args(study_id):
        if not isinstance(study_id, int):
            raise ApiError("invalid_study_id", "This study id is invalid: " + str(study_id))

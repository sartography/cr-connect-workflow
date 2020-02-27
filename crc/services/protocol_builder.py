import json
from typing import List, Optional

import requests

from crc import app
from models.protocol_builder import ProtocolBuilderStudy, ProtocolBuilderStudySchema, ProtocolBuilderInvestigator, \
    ProtocolBuilderRequiredDocument, ProtocolBuilderStudyDetails, ProtocolBuilderInvestigatorSchema, \
    ProtocolBuilderRequiredDocumentSchema, ProtocolBuilderStudyDetailsSchema


class ProtocolBuilderService(object):
    STUDY_URL = app.config['PB_USER_STUDIES_URL']
    INVESTIGATOR_URL = app.config['PB_INVESTIGATORS_URL']
    REQUIRED_DOCS_URL = app.config['PB_REQUIRED_DOCS_URL']
    STUDY_DETAILS_URL = app.config['PB_STUDY_DETAILS_URL']

    @staticmethod
    def get_studies(user_id) -> Optional[List[ProtocolBuilderStudy]]:
        response = requests.get(ProtocolBuilderService.STUDY_URL % user_id)
        if response.ok and response.text:
            pb_studies = ProtocolBuilderStudySchema(many=True).loads(response.text)
            return pb_studies
        else:
            return None

    @staticmethod
    def get_investigators(study_id) -> Optional[List[ProtocolBuilderInvestigator]]:
        response = requests.get(ProtocolBuilderService.INVESTIGATOR_URL % study_id)
        if response.ok and response.text:
            pb_studies = ProtocolBuilderInvestigatorSchema(many=True).loads(response.text)
            return pb_studies
        else:
            return None

    @staticmethod
    def get_required_docs(study_id) -> Optional[List[ProtocolBuilderRequiredDocument]]:
        response = requests.get(ProtocolBuilderService.REQUIRED_DOCS_URL % study_id)
        if response.ok and response.text:
            pb_studies = ProtocolBuilderRequiredDocumentSchema(many=True).loads(response.text)
            return pb_studies
        else:
            return None

    @staticmethod
    def get_study_details(study_id) -> Optional[ProtocolBuilderStudyDetails]:
        response = requests.get(ProtocolBuilderService.STUDY_DETAILS_URL % study_id)
        if response.ok and response.text:
            pb_study_details = ProtocolBuilderStudyDetailsSchema().loads(response.text)
            return pb_study_details
        else:
            return None

import json
from json import JSONDecodeError
from typing import List, Optional

import requests
from SpiffWorkflow.util.metrics import timeit

from crc import app
from crc.api.common import ApiError
from crc.models.protocol_builder import ProtocolBuilderCreatorStudySchema, ProtocolBuilderRequiredDocument


class ProtocolBuilderService(object):
    STUDY_URL = app.config['PB_USER_STUDIES_URL']
    INVESTIGATOR_URL = app.config['PB_INVESTIGATORS_URL']
    REQUIRED_DOCS_URL = app.config['PB_REQUIRED_DOCS_URL']
    STUDY_DETAILS_URL = app.config['PB_STUDY_DETAILS_URL']
    SPONSORS_URL = app.config['PB_SPONSORS_URL']
    IRB_INFO_URL = app.config['PB_IRB_INFO_URL']
    CHECK_STUDY_URL = app.config['PB_CHECK_STUDY_URL']

    @staticmethod
    def is_enabled():
        if isinstance(app.config['PB_ENABLED'], str):
            return app.config['PB_ENABLED'].lower() == "true"
        else:
            return app.config['PB_ENABLED'] is True

    @staticmethod
    def get_studies(user_id) -> {}:
        ProtocolBuilderService.__enabled_or_raise()
        if not isinstance(user_id, str):
            raise ApiError("protocol_builder_error", "This user id is invalid: " + str(user_id))
        url = ProtocolBuilderService.STUDY_URL % user_id
        response = requests.get(url)
        if response.ok and response.text:
            try:
                pb_studies = ProtocolBuilderCreatorStudySchema(many=True).loads(response.text)
                return pb_studies
            except JSONDecodeError as err:
                raise ApiError("protocol_builder_error",
                               "Received an invalid response from the protocol builder.  The response is not "
                               "valid json. Url: %s, Response: %s, error: %s" %
                               (url, response.text, err.msg))
        else:
            raise ApiError("protocol_builder_error",
                           "Received an invalid response from the protocol builder (status %s): %s" %
                           (response.status_code, response.text))

    @staticmethod
    def get_investigators(study_id) -> {}:
        return ProtocolBuilderService.__make_request(study_id, ProtocolBuilderService.INVESTIGATOR_URL)

    @staticmethod
    def get_required_docs(study_id) -> Optional[List[ProtocolBuilderRequiredDocument]]:
        return ProtocolBuilderService.__make_request(study_id, ProtocolBuilderService.REQUIRED_DOCS_URL)

    @staticmethod
    def get_study_details(study_id) -> {}:
        return ProtocolBuilderService.__make_request(study_id, ProtocolBuilderService.STUDY_DETAILS_URL)

    @staticmethod
    def get_irb_info(study_id) -> {}:
        return ProtocolBuilderService.__make_request(study_id, ProtocolBuilderService.IRB_INFO_URL)

    @staticmethod
    def get_sponsors(study_id) -> {}:
        return ProtocolBuilderService.__make_request(study_id, ProtocolBuilderService.SPONSORS_URL)

    @staticmethod
    def check_study(study_id) -> {}:
        return ProtocolBuilderService.__make_request(study_id, ProtocolBuilderService.CHECK_STUDY_URL)

    @staticmethod
    def __enabled_or_raise():
        if not ProtocolBuilderService.is_enabled():
            raise ApiError("protocol_builder_disabled", "The Protocol Builder Service is currently disabled.")

    @staticmethod
    def __make_request(study_id, url):
        ProtocolBuilderService.__enabled_or_raise()
        if not isinstance(study_id, int):
            raise ApiError("invalid_study_id", "This study id is invalid: " + str(study_id))
        response = requests.get(url % study_id)
        if response.ok and response.text:
            return json.loads(response.text)
        else:
            raise ApiError("protocol_builder_error",
                           "Received an invalid response from the protocol builder (status %s): %s when calling "
                           "url '%s'." %
                           (response.status_code, response.text, url))

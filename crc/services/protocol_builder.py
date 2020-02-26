import json

import requests

from crc import app

STUDY_URL = app.config['PB_USER_STUDIES_URL']
INVESTIGATOR_URL = app.config['PB_INVESTIGATORS_URL']
REQUIRED_DOCS_URL = app.config['PB_REQUIRED_DOCS_URL']
STUDY_DETAILS_URL = app.config['PB_STUDY_DETAILS_URL']




def get_studies(user_id):
    response = requests.get(STUDY_URL % user_id)
    if response.ok:
        return json.loads(response.text)
    else:
        return None


def get_investigators(study_id):
    response = requests.get(INVESTIGATOR_URL % study_id)
    if response.ok:
        return json.loads(response.text)
    else:
        return None


def get_required_docs(study_id):
    response = requests.get(REQUIRED_DOCS_URL % study_id)
    if response.ok:
        return json.loads(response.text)
    else:
        return None


def get_study_details(study_id):
    response = requests.get(STUDY_DETAILS_URL % study_id)
    if response.ok:
        return json.loads(response.text)
    else:
        return None

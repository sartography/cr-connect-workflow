from datetime import datetime

from flask import g
from sqlalchemy.exc import IntegrityError
import json
from crc import session
from crc.scripts.script import DataStoreBase
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.data_store import DataStoreModel


def study_data_set(study_id,key,value):
    """Set a study data value in the data_store, mimic the script endpoint"""
    if study_id is None:
        raise ApiError('unknown_study', 'Please provide a valid Study ID.')

    if key is None:
        raise ApiError('invalid_key', 'Please provide a valid key')
    dsb = DataStoreBase()
    retval=dsb.set_data_common('api',study_id,None,None,None,'api_study_data_set',key,value)
    json_value = json.dumps(retval, ensure_ascii=False, indent=2)
    return json_value

def study_data_get(study_id,key,default=None):
    """Set a study data value in the data_store, mimic the script endpoint"""
    if study_id is None:
        raise ApiError('unknown_study', 'Please provide a valid Study ID.')

    if key is None:
        raise ApiError('invalid_key', 'Please provide a valid key')
    dsb = DataStoreBase()
    retval=dsb.get_data_common(study_id,None,'api_study_data_get',key,default)
    json_value = json.dumps(retval, ensure_ascii=False, indent=2)
    return json_value


def user_data_set(user_id,key,value):
    """Set a user data value in the data_store, mimic the script endpoint"""
    if user_id is None:
        raise ApiError('unknown_study', 'Please provide a valid UserID.')

    if key is None:
        raise ApiError('invalid_key', 'Please provide a valid key')
    dsb = DataStoreBase()

    retval=dsb.set_data_common('api',
                               None,
                               user_id,
                               None,
                               None,
                               'api_user_data_set',
                               key,value)

    json_value = json.dumps(retval, ensure_ascii=False, indent=2)
    return json_value


def user_data_get(user_id,key,default=None):
    """Set a user data value in the data_store, mimic the script endpoint"""
    if user_id is None:
        raise ApiError('unknown_study', 'Please provide a valid UserID.')

    if key is None:
        raise ApiError('invalid_key', 'Please provide a valid key')
    dsb = DataStoreBase()
    retval=dsb.get_data_common(None,
                               user_id,
                               'api_user_data_get',
                               key,default)

    json_value = json.dumps(retval, ensure_ascii=False, indent=2)
    return json_value


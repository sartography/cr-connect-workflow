from datetime import datetime

from flask import g
from sqlalchemy.exc import IntegrityError
import json
from crc import session
from crc.scripts.script import DataStoreBase
from crc.api.common import ApiError, ApiErrorSchema
from crc.models.data_store import DataStoreModel,DataStoreSchema


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
    """Get a study data value in the data_store, mimic the script endpoint"""
    if study_id is None:
        raise ApiError('unknown_study', 'Please provide a valid Study ID.')

    if key is None:
        raise ApiError('invalid_key', 'Please provide a valid key')
    dsb = DataStoreBase()
    retval=dsb.get_data_common(study_id,None,'api_study_data_get',key,default)
    json_value = json.dumps(retval, ensure_ascii=False, indent=2)
    return json_value

def study_multi_get(study_id):
    """Get all data_store values for a given study_id study"""
    if study_id is None:
        raise ApiError('unknown_study', 'Please provide a valid Study ID.')

    dsb = DataStoreBase()
    retval=dsb.get_multi_common(study_id,None)
    results = DataStoreSchema(many=True).dump(retval)
    return results




def study_data_del(study_id,key):
    """Delete a study data value in the data store"""
    if study_id is None:
        raise ApiError('unknown_study', 'Please provide a valid Study ID.')

    if key is None:
        raise ApiError('invalid_key', 'Please provide a valid key')
    dsb = DataStoreBase()
    dsb.del_data_common(study_id,None,'api_study_data_get',key)
    json_value = json.dumps('deleted', ensure_ascii=False, indent=2)
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
    """Get a user data value from the data_store, mimic the script endpoint"""
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

def user_multi_get(user_id):
    """Get all data values in the data_store for a userid"""
    if user_id is None:
        raise ApiError('unknown_study', 'Please provide a valid UserID.')

    dsb = DataStoreBase()
    retval=dsb.get_multi_common(None,
                               user_id)
    results = DataStoreSchema(many=True).dump(retval)
    return results



def user_data_del(user_id,key):
    """Delete a data store item for a user_id and a key"""
    if user_id is None:
        raise ApiError('unknown_study', 'Please provide a valid UserID.')

    if key is None:
        raise ApiError('invalid_key', 'Please provide a valid key')
    dsb = DataStoreBase()
    dsb.del_data_common(None,
                               user_id,
                               'api_user_data_get',
                               key)

    json_value = json.dumps('deleted', ensure_ascii=False, indent=2)
    return json_value


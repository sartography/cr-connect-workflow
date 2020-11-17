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
    retval = dsb.get_data_common(study_id,None,'api_study_data_get',key,default)
    #json_value = json.dumps(retval, ensure_ascii=False, indent=2) # just return raw text
    return retval

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

    #json_value = json.dumps(retval, ensure_ascii=False, indent=2) # just return raw text
    return retval

def user_multi_get(user_id):
    """Get all data values in the data_store for a userid"""
    if user_id is None:
        raise ApiError('unknown_study', 'Please provide a valid UserID.')

    dsb = DataStoreBase()
    retval=dsb.get_multi_common(None,
                               user_id)
    results = DataStoreSchema(many=True).dump(retval)
    return results



def datastore_del(id):
    """Delete a data store item for a user_id and a key"""
    session.query(DataStoreModel).filter_by(id=id).delete()
    session.commit()
    json_value = json.dumps('deleted', ensure_ascii=False, indent=2)
    return json_value

def datastore_get(id):
    """Delete a data store item for a user_id and a key"""
    item = session.query(DataStoreModel).filter_by(id=id).first()
    results = DataStoreSchema(many=False).dump(item)
    return results

def update_datastore(id, body):
    """allow a modification to a datastore item """
    if id is None:
        raise ApiError('unknown_id', 'Please provide a valid ID.')

    item = session.query(DataStoreModel).filter_by(id=id).first()
    if item is None:
        raise ApiError('unknown_item', 'The item "' + id + '" is not recognized.')
    print(body)
    # I'm not sure if there is a generic way to use the
    # schema to both parse the body and update the SQLAlchemy record
    for key in body:
        if hasattr(item,key):
            setattr(item,key,body[key])
    item.last_updated = datetime.now()
    session.add(item)
    session.commit()
    return DataStoreSchema().dump(item)


def add_datastore(body):
    """ add a new datastore item """

    print(body)
    if body.get(id,None):
        raise ApiError('id_specified', 'You may not specify an id for a new datastore item')

    if 'key' not in body:
        raise ApiError('no_key', 'You need to specify a key to add a datastore item')

    if 'value' not in body:
        raise ApiError('no_value', 'You need to specify a value to add a datastore item')

    if (not 'user_id' in body) and (not 'study_id' in body):
        raise ApiError('conflicting_values', 'A datastore item should have either a study_id or a user_id')


    if 'user_id' in body and 'study_id' in body:
        raise ApiError('conflicting_values', 'A datastore item should have either a study_id or a user_id, '
                                             'but not both')

    item = DataStoreModel(key=body['key'],value=body['value'])
    # I'm not sure if there is a generic way to use the
    # schema to both parse the body and update the SQLAlchemy record
    for key in body:
        if hasattr(item,key):
            setattr(item,key,body[key])
    item.last_updated = datetime.now()
    session.add(item)
    session.commit()
    return DataStoreSchema().dump(item)

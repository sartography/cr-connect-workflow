import json
from datetime import datetime

from crc import session
from crc.api.common import ApiError
from crc.models.data_store import DataStoreModel, DataStoreSchema
from crc.scripts.data_store_base import DataStoreBase
from crc.models.file import FileModel

def study_multi_get(study_id):
    """Get all data_store values for a given study_id study"""
    if study_id is None:
        raise ApiError('unknown_study', 'Please provide a valid Study ID.')

    dsb = DataStoreBase()
    retval = dsb.get_multi_common(study_id, None)
    results = DataStoreSchema(many=True).dump(retval)
    return results


def user_multi_get(user_id):
    """Get all data values in the data_store for a userid"""
    if user_id is None:
        raise ApiError('unknown_study', 'Please provide a valid UserID.')

    dsb = DataStoreBase()
    retval = dsb.get_multi_common(None,
                                  user_id)
    results = DataStoreSchema(many=True).dump(retval)
    return results


def file_multi_get(file_id):
    """Get all data values in the data store for a file_id"""
    if file_id is None:
        raise ApiError(code='unknown_file', message='Please provide a valid file id.')
    dsb = DataStoreBase()
    retval = dsb.get_multi_common(None, None, file_id=file_id)
    results = DataStoreSchema(many=True).dump(retval)
    return results


def datastore_del(id):
    """Delete a data store item for a key"""
    session.query(DataStoreModel).filter_by(id=id).delete()
    session.commit()
    json_value = json.dumps('deleted', ensure_ascii=False, indent=2)
    return json_value


def datastore_get(id):
    """retrieve a data store item by a key"""
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

    DataStoreSchema().load(body, instance=item, session=session)
    item.last_updated = datetime.utcnow()
    session.add(item)
    session.commit()
    return DataStoreSchema().dump(item)


def add_datastore(body):
    """ add a new datastore item """

    print(body)
    if body.get(id, None):
        raise ApiError('id_specified', 'You may not specify an id for a new datastore item')

    if 'key' not in body:
        raise ApiError('no_key', 'You need to specify a key to add a datastore item')

    if 'value' not in body:
        raise ApiError('no_value', 'You need to specify a value to add a datastore item')

    if ('user_id' not in body) and ('study_id' not in body)  and ('file_id' not in body):
        raise ApiError('conflicting_values', 'A datastore item should have either a study_id, user_id or file_id ')


    present = 0
    for field in ['user_id','study_id','file_id']:
        if field in body:
            present = present+1
    if present > 1:
        raise ApiError('conflicting_values', 'A datastore item should have one of a study_id, user_id or a file_id '
                                             'but not more than one of these')

    item = DataStoreSchema().load(body)
    item.last_updated = datetime.utcnow()
    session.add(item)
    session.commit()
    return DataStoreSchema().dump(item)

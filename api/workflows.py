import datetime
from typing import Tuple, Any, Union, Dict

from connexion import NoContent

workflows = {
    1: {
        'id': 1,
        'tag': 'expedited',
        'name': 'Full IRB Board Review',
        'last_updated': datetime.datetime.now(),
    }
}


def list_all(limit=100):
    # NOTE: we need to wrap it with list for Python 3 as dict_values is not JSON serializable
    return list(workflows.values())[0:limit]


def get(workflow_id: int) -> Union[Tuple[Any, int], Dict[str, Union[int, str, datetime]]]:
    id_ = int(workflow_id)
    if workflows.get(id_) is None:
        return NoContent, 404
    return workflows[id_]

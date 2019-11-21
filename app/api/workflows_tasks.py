import datetime

from connexion import NoContent

workflow_tasks = [
    {
        'id': 1,
        'workflow_id': 1,
        'task_id': 1,
        'last_updated': datetime.datetime.now(),
        'status': 'Complete',
    },
    {
        'id': 2,
        'workflow_id': 1,
        'task_id': 2,
        'last_updated': datetime.datetime.now(),
        'status': 'Incomplete',
    },
    {
        'id': 3,
        'workflow_id': 1,
        'task_id': 3,
        'last_updated': datetime.datetime.now(),
        'status': 'Disabled',
    },
    {
        'id': 4,
        'workflow_id': 1,
        'task_id': 4,
        'last_updated': datetime.datetime.now(),
        'status': 'Incomplete',
    },
]


def start(workflow_id):
    # spec = TrainingWorkflowSpec()
    # wf = Workflow(spec)
    id_ = len(workflow_tasks)
    workflow_tasks.append({
        'id': id_,
        'workflow_id': workflow_id,
        'task_id': 1,
        'last_updated': datetime.datetime.now(),
        'status': 'Incomplete',
    })
    return workflow_tasks[id_]


def get(workflow_id, task_id):
    i = _get_workflow_task_index(workflow_id, task_id)
    print(i)
    return workflow_tasks[i] if i is not None else NoContent, 404


def post(workflow_id, task_id, body):
    i = _get_workflow_task_index(workflow_id, task_id)

    if i is not None:
        workflow_tasks[i]['last_updated'] = datetime.datetime.now()
        workflow_tasks[i]['status'] = body['status']

        return workflow_tasks[i]
    else:
        return NoContent, 404


def delete(workflow_id, task_id):
    i = _get_workflow_task_index(workflow_id, task_id)

    if i is not None:
        del workflow_tasks[i]
        return NoContent, 204
    else:
        return NoContent, 404


def _get_workflow_task_index(workflow_id, task_id):
    workflow_id = int(workflow_id)
    task_id = int(task_id)
    for i, wt in enumerate(workflow_tasks):
        if wt['workflow_id'] == workflow_id and wt['task_id'] == task_id:
            return i
    return None

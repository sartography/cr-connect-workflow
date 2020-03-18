from datetime import datetime

from flask import g

from crc import session, auth
from crc.models.stats import WorkflowStatsModel, WorkflowStatsModelSchema, TaskEventModel, TaskEventModelSchema


@auth.login_required
def get_workflow_stats(workflow_id):
    workflow_model = session.query(WorkflowStatsModel).filter_by(workflow_id=workflow_id).first()
    return WorkflowStatsModelSchema().dump(workflow_model)


@auth.login_required
def update_workflow_stats(workflow_model, workflow_api_model):
    stats = session.query(WorkflowStatsModel) \
        .filter_by(study_id=workflow_model.study_id) \
        .filter_by(workflow_id=workflow_model.id) \
        .filter_by(workflow_spec_id=workflow_model.workflow_spec_id) \
        .filter_by(spec_version=workflow_model.spec_version) \
        .first()

    if stats is None:
        stats = WorkflowStatsModel(
            study_id=workflow_model.study_id,
            workflow_id=workflow_model.id,
            workflow_spec_id=workflow_model.workflow_spec_id,
            spec_version=workflow_model.spec_version,
        )

    complete_states = ['CANCELLED', 'COMPLETED']
    incomplete_states = ['MAYBE', 'LIKELY', 'FUTURE', 'WAITING', 'READY']
    tasks = list(workflow_api_model.user_tasks)
    stats.num_tasks_total = len(tasks)
    stats.num_tasks_complete = sum(1 for t in tasks if t.state in complete_states)
    stats.num_tasks_incomplete = sum(1 for t in tasks if t.state in incomplete_states)
    stats.last_updated = datetime.now()

    session.add(stats)
    session.commit()
    return WorkflowStatsModelSchema().dump(stats)


@auth.login_required
def log_task_complete(workflow_model, task_id):
    task_event = TaskEventModel(
        study_id=workflow_model.study_id,
        user_uid=g.user.uid,
        workflow_id=workflow_model.id,
        workflow_spec_id=workflow_model.workflow_spec_id,
        spec_version=workflow_model.spec_version,
        task_id=task_id,
        task_state='COMPLETE',
        date=datetime.now(),
    )
    session.add(task_event)
    session.commit()
    return TaskEventModelSchema().dump(task_event)

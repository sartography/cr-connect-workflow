"""empty message

Revision ID: ac1141d29d37
Revises: 8580676e5302
Create Date: 2021-10-06 14:05:58.062277

"""
import re

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
from crc.models.workflow import WorkflowSpecModel, WorkflowModel

revision = 'ac1141d29d37'
down_revision = '8580676e5302'
branch_labels = None
depends_on = None


def upgrade():
    print("Doing the upgrade")
    op.execute('ALTER TABLE workflow DROP CONSTRAINT workflow_workflow_spec_id_fkey')
    op.execute('ALTER TABLE file DROP CONSTRAINT file_workflow_spec_id_fkey')
    op.execute('ALTER TABLE workflow_library DROP CONSTRAINT workflow_library_workflow_spec_id_fkey')
    op.execute('ALTER TABLE workflow_library DROP CONSTRAINT workflow_library_library_spec_id_fkey')
    op.execute('ALTER TABLE task_event DROP CONSTRAINT task_event_workflow_spec_id_fkey')
    # Use Alchemy's connection and transaction to noodle over the data.
    connection = op.get_bind()

    # Select all existing names that need migrating.
    results = connection.execute(sa.select([
        WorkflowSpecModel.id,
        WorkflowSpecModel.display_name,
    ])).fetchall()
    # Iterate over all selected data tuples.
    for id, display_name in results:
        new_id = display_name.lower().\
            replace(",", "").\
            replace("'", "").\
            replace(" ", "_").\
            replace("-", "_").\
            replace(".", "_").\
            replace("/","_").\
            replace("\\", "_")
        old_id = id
        op.execute("Update workflow_spec set id='%s' where id='%s'" % (new_id, old_id))
        op.execute("Update workflow set workflow_spec_id='%s' where workflow_spec_id='%s'" % (new_id, old_id))
        op.execute("Update file set workflow_spec_id='%s' where workflow_spec_id='%s'" % (new_id, old_id))
        op.execute("Update workflow_library set workflow_spec_id='%s' where workflow_spec_id='%s'" % (new_id, old_id))
        op.execute("Update workflow_library set library_spec_id='%s' where library_spec_id='%s'" % (new_id, old_id))
        op.execute("Update task_event set workflow_spec_id='%s' where workflow_spec_id='%s'" % (new_id, old_id))
    op.create_foreign_key(
        'workflow_workflow_spec_id_fkey',
        'workflow', 'workflow_spec',
        ['workflow_spec_id'], ['id'],
    )
    op.create_foreign_key(
        'file_workflow_spec_id_fkey',
        'file', 'workflow_spec',
        ['workflow_spec_id'], ['id'],
    )
    op.create_foreign_key(
        'workflow_library_workflow_spec_id_fkey',
        'workflow_library', 'workflow_spec',
        ['workflow_spec_id'], ['id'],
    )
    op.create_foreign_key(
        'workflow_library_library_spec_id_fkey',
        'workflow_library', 'workflow_spec',
        ['library_spec_id'], ['id'],
    )
    op.create_foreign_key(
        'task_event_workflow_spec_id_fkey',
        'task_event', 'workflow_spec',
        ['workflow_spec_id'], ['id'],
    )


def downgrade():
    pass

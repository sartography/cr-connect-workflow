"""empty message

Revision ID: ac1141d29d37
Revises: 8580676e5302
Create Date: 2021-10-06 14:05:58.062277

"""
import re

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.

revision = 'ac1141d29d37'
down_revision = '8580676e5302'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE workflow DROP CONSTRAINT workflow_workflow_spec_id_fkey')
    op.execute('ALTER TABLE file DROP CONSTRAINT file_workflow_spec_id_fkey')
    op.execute('ALTER TABLE workflow_library DROP CONSTRAINT workflow_library_workflow_spec_id_fkey')
    op.execute('ALTER TABLE workflow_library DROP CONSTRAINT workflow_library_library_spec_id_fkey')
    op.execute('ALTER TABLE task_event DROP CONSTRAINT task_event_workflow_spec_id_fkey')

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

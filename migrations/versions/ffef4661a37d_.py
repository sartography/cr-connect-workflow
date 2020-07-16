"""empty message

Revision ID: ffef4661a37d
Revises: 5acd138e969c
Create Date: 2020-07-14 19:52:05.270939

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ffef4661a37d'
down_revision = '5acd138e969c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('task_event', sa.Column('task_lane', sa.String(), nullable=True))
    op.drop_constraint('task_event_user_uid_fkey', 'task_event', type_='foreignkey')
    op.execute("update task_event set action = 'COMPLETE' where action='Complete'")
    op.execute("update task_event set action = 'TOKEN_RESET' where action='Backwards Move'")
    op.execute("update task_event set action = 'HARD_RESET' where action='Restart (Hard)'")
    op.execute("update task_event set action = 'SOFT_RESET' where action='Restart (Soft)'")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key('task_event_user_uid_fkey', 'task_event', 'user', ['user_uid'], ['uid'])
    op.drop_column('task_event', 'task_lane')
    op.execute("update task_event set action = 'Complete' where action='COMPLETE'")
    op.execute("update task_event set action = 'Backwards Move' where action='TOKEN_RESET'")
    op.execute("update task_event set action = 'Restart (Hard)' where action='HARD_RESET'")
    op.execute("update task_event set action = 'Restart (Soft)' where action='SOFT_RESET'")
    # ### end Alembic commands ###

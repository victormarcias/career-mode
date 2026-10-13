"""remove the ai_interview and video_task event types

The events of those two types become notes, keeping the old name at the start of their notes, so nothing is lost.
Then the `type_valid` rule of `events` no longer lists them.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13 12:00:00.000000
"""
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

KEPT = ['application', 'passive_message', 'note', 'tech_filter', 'hr_intro', 'tech_interview', 'culture_interview',
        'on_hold', 'offer', 'rejection', 'red_flag', 'archive', 'pending']
ALL = ['application', 'passive_message', 'note', 'tech_filter', 'hr_intro', 'tech_interview', 'ai_interview',
       'culture_interview', 'video_task', 'on_hold', 'offer', 'rejection', 'red_flag', 'archive', 'pending']


def _rule(types):
    return "type IN (%s)" % ', '.join("'%s'" % t for t in types)


def upgrade():
    for old, label in (('ai_interview', 'AI interview'), ('video_task', 'Video task')):
        op.execute(
            "UPDATE events SET notes = CASE WHEN notes = '' THEN '%s' ELSE '%s: ' || notes END, type = 'note' WHERE type = '%s'"
            % (label, label, old)
        )
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_events_type_valid'), type_='check')
        batch_op.create_check_constraint('type_valid', _rule(KEPT))


def downgrade():
    # the two types are allowed again; the events that became notes stay notes
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_events_type_valid'), type_='check')
        batch_op.create_check_constraint('type_valid', _rule(ALL))

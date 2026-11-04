"""a passive message needs an agency or a client

A recruiter of a company that hires directly writes for a client, so the passive message of a client with no agency
is valid. The `passive_message_has_agency` rule of `events` becomes `passive_message_has_company`.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-21 12:00:00.000000
"""
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_events_passive_message_has_agency'), type_='check')
        batch_op.create_check_constraint(
            'passive_message_has_company', "type <> 'passive_message' OR agency_id IS NOT NULL OR client_id IS NOT NULL")


def downgrade():
    # a passive message of a client with no agency cannot stay: it becomes a note
    op.execute("UPDATE events SET type = 'note' WHERE type = 'passive_message' AND agency_id IS NULL")
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_events_passive_message_has_company'), type_='check')
        batch_op.create_check_constraint('passive_message_has_agency', "type <> 'passive_message' OR agency_id IS NOT NULL")

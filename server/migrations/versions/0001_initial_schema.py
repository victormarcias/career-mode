"""initial schema

The first version of the schema. Once it has run anywhere, never edit it: change a
model and run `alembic revision --autogenerate -m "what changed"` for a new revision.

Revision ID: 0001
Revises: 
Create Date: 2026-10-08 12:12:12.790409
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('agencies',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(collation='NOCASE'), nullable=False),
    sa.Column('type', sa.String(), server_default='', nullable=False),
    sa.Column('website', sa.String(), nullable=True),
    sa.Column('linkedin', sa.String(), nullable=True),
    sa.Column('application_link', sa.String(), nullable=True),
    sa.Column('status', sa.String(), server_default='active', nullable=False),
    sa.CheckConstraint("status IN ('active', 'archived')", name=op.f('ck_agencies_status_valid')),
    sa.CheckConstraint('length(trim(name)) > 0', name=op.f('ck_agencies_name_not_blank')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_agencies')),
    sa.UniqueConstraint('name', name=op.f('uq_agencies_name'))
    )
    op.create_table('agency_recruiters',
    sa.Column('agency_id', sa.String(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], name=op.f('fk_agency_recruiters_agency_id_agencies'), onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('agency_id', 'position', name=op.f('pk_agency_recruiters'))
    )
    op.create_table('clients',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(collation='NOCASE'), nullable=False),
    sa.Column('website', sa.String(), nullable=True),
    sa.Column('linkedin', sa.String(), nullable=True),
    sa.Column('notes', sa.String(), server_default='', nullable=False),
    sa.Column('via_agency_id', sa.String(), nullable=True),
    sa.CheckConstraint('length(trim(name)) > 0', name=op.f('ck_clients_name_not_blank')),
    sa.ForeignKeyConstraint(['via_agency_id'], ['agencies.id'], name=op.f('fk_clients_via_agency_id_agencies'), onupdate='CASCADE', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_clients')),
    sa.UniqueConstraint('name', name=op.f('uq_clients_name'))
    )
    op.create_table('events',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('date', sa.String(), nullable=False),
    sa.Column('time', sa.String(), nullable=True),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('agency_id', sa.String(), nullable=True),
    sa.Column('client_id', sa.String(), nullable=True),
    sa.Column('notes', sa.String(), server_default='', nullable=False),
    sa.Column('jd_url', sa.String(), nullable=True),
    sa.Column('apply_type', sa.String(), nullable=True),
    sa.Column('calendar_event_id', sa.String(), nullable=True),
    sa.Column('created_at', sa.String(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))"), nullable=False),
    sa.CheckConstraint("apply_type IS NULL OR apply_type IN ('email_apply', 'web_form')", name=op.f('ck_events_apply_type_valid')),
    sa.CheckConstraint("date GLOB '[0-9][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]'", name=op.f('ck_events_date_format')),
    sa.CheckConstraint("time IS NULL OR time GLOB '[0-2][0-9]:[0-5][0-9]'", name=op.f('ck_events_time_format')),
    sa.CheckConstraint("type <> 'passive_message' OR agency_id IS NOT NULL", name=op.f('ck_events_passive_message_has_agency')),
    sa.CheckConstraint("type IN ('application', 'passive_message', 'note', 'tech_filter', 'hr_intro', 'tech_interview', 'ai_interview', 'culture_interview', 'video_task', 'on_hold', 'offer', 'rejection', 'red_flag', 'archive', 'pending')", name=op.f('ck_events_type_valid')),
    sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], name=op.f('fk_events_agency_id_agencies'), onupdate='CASCADE', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name=op.f('fk_events_client_id_clients'), onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_events')),
    sa.UniqueConstraint('calendar_event_id', name=op.f('uq_events_calendar_event_id'))
    )
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_events_agency_id'), ['agency_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_events_client_id'), ['client_id'], unique=False)



def downgrade():
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_events_client_id'))
        batch_op.drop_index(batch_op.f('ix_events_agency_id'))

    op.drop_table('events')
    op.drop_table('clients')
    op.drop_table('agency_recruiters')
    op.drop_table('agencies')

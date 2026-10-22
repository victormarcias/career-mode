"""merge agencies and clients into companies

One `companies` table with a `company_type` (agency or client) replaces `agencies` and `clients`, so a name is
unique whichever it is. An agency's `type` (what it does) and a client's `notes` become `notes`; a client's
`via_agency_id` becomes `via_company_id`; `agency_recruiters` becomes `company_recruiters`. An event has a
`company_id` (its client, else its agency) and a `via_company_id` (the agency, when it has a client too). The
stored `status` of an agency goes away: it is derived from the events, as a client's always was.

A client whose id or name an agency already has gets a new id (`-2`) or the name with " (client)" after it.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

TYPES = ['application', 'passive_message', 'note', 'tech_filter', 'hr_intro', 'tech_interview', 'culture_interview',
         'on_hold', 'offer', 'rejection', 'red_flag', 'archive', 'pending']
CLOSING = ('rejection', 'red_flag', 'on_hold', 'offer', 'archive')


def _in(column, values):
    return '%s IN (%s)' % (column, ', '.join("'%s'" % v for v in values))


def _events_table(name, company_columns, passive_rule, extra_checks):
    return op.create_table(
        name,
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('date', sa.String(), nullable=False),
        sa.Column('time', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        *company_columns,
        sa.Column('notes', sa.String(), server_default='', nullable=False),
        sa.Column('jd_url', sa.String(), nullable=True),
        sa.Column('apply_type', sa.String(), nullable=True),
        sa.Column('calendar_event_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))"), nullable=False),
        sa.CheckConstraint("apply_type IS NULL OR apply_type IN ('email_apply', 'web_form')", name=op.f('ck_events_apply_type_valid')),
        sa.CheckConstraint("date GLOB '[0-9][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]'", name=op.f('ck_events_date_format')),
        sa.CheckConstraint("time IS NULL OR time GLOB '[0-2][0-9]:[0-5][0-9]'", name=op.f('ck_events_time_format')),
        sa.CheckConstraint(passive_rule, name=op.f('ck_events_passive_message_has_company')),
        sa.CheckConstraint(_in('type', TYPES), name=op.f('ck_events_type_valid')),
        *extra_checks,
        sa.PrimaryKeyConstraint('id', name=op.f('pk_events')),
        sa.UniqueConstraint('calendar_event_id', name=op.f('uq_events_calendar_event_id')),
    )


def upgrade():
    bind = op.get_bind()
    op.create_table(
        'companies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(collation='NOCASE'), nullable=False),
        sa.Column('company_type', sa.String(), nullable=False),
        sa.Column('notes', sa.String(), server_default='', nullable=False),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('linkedin', sa.String(), nullable=True),
        sa.Column('application_link', sa.String(), nullable=True),
        sa.Column('via_company_id', sa.String(), nullable=True),
        sa.CheckConstraint("company_type IN ('agency', 'client')", name=op.f('ck_companies_company_type_valid')),
        sa.CheckConstraint('length(trim(name)) > 0', name=op.f('ck_companies_name_not_blank')),
        sa.CheckConstraint("via_company_id IS NULL OR company_type = 'client'", name=op.f('ck_companies_only_a_client_has_a_via')),
        sa.ForeignKeyConstraint(['via_company_id'], ['companies.id'], name=op.f('fk_companies_via_company_id_companies'),
                                onupdate='CASCADE', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_companies')),
        sa.UniqueConstraint('name', name=op.f('uq_companies_name')),
    )
    op.create_table(
        'company_recruiters',
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_company_recruiters_company_id_companies'),
                                onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('company_id', 'position', name=op.f('pk_company_recruiters')),
    )

    insert = sa.text(
        'INSERT INTO companies (id, name, company_type, notes, website, linkedin, application_link, via_company_id) '
        'VALUES (:id, :name, :company_type, :notes, :website, :linkedin, :application_link, :via)')
    agencies = bind.execute(sa.text('SELECT id, name, type, website, linkedin, application_link FROM agencies')).fetchall()
    for a in agencies:
        bind.execute(insert, dict(id=a.id, name=a.name, company_type='agency', notes=a.type or '', website=a.website,
                                  linkedin=a.linkedin, application_link=a.application_link, via=None))
    bind.execute(sa.text('INSERT INTO company_recruiters (company_id, position, url) SELECT agency_id, position, url FROM agency_recruiters'))

    ids = {a.id for a in agencies}
    names = {a.name.lower() for a in agencies}
    client_ids = {}
    clients = bind.execute(sa.text('SELECT id, name, website, linkedin, notes, via_agency_id FROM clients')).fetchall()
    for c in clients:
        new_id, n = c.id, 2
        while new_id in ids:
            new_id, n = '%s-%d' % (c.id, n), n + 1
        name = c.name
        while name.lower() in names:
            name = '%s (client)' % name
        ids.add(new_id)
        names.add(name.lower())
        client_ids[c.id] = new_id
        bind.execute(insert, dict(id=new_id, name=name, company_type='client', notes=c.notes or '', website=c.website,
                                  linkedin=c.linkedin, application_link=None, via=c.via_agency_id))

    _events_table('events_new', [
        sa.Column('company_id', sa.String(), nullable=True),
        sa.Column('via_company_id', sa.String(), nullable=True),
    ], "type <> 'passive_message' OR company_id IS NOT NULL", [
        sa.CheckConstraint('via_company_id IS NULL OR company_id IS NOT NULL', name=op.f('ck_events_via_needs_a_company')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_events_company_id_companies'), onupdate='CASCADE', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['via_company_id'], ['companies.id'], name=op.f('fk_events_via_company_id_companies'), onupdate='CASCADE', ondelete='RESTRICT'),
    ])
    columns = 'id, date, time, type, notes, jd_url, apply_type, calendar_event_id, created_at'
    bind.execute(sa.text(
        'INSERT INTO events_new (%s, company_id, via_company_id) SELECT %s, agency_id, NULL FROM events WHERE client_id IS NULL' % (columns, columns)))
    for old, new in client_ids.items():
        bind.execute(sa.text(
            'INSERT INTO events_new (%s, company_id, via_company_id) SELECT %s, :new, agency_id FROM events WHERE client_id = :old' % (columns, columns)),
            dict(new=new, old=old))
    op.drop_table('events')
    op.rename_table('events_new', 'events')
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_events_company_id'), ['company_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_events_via_company_id'), ['via_company_id'], unique=False)
    op.drop_table('clients')
    op.drop_table('agency_recruiters')
    op.drop_table('agencies')


def _status(rows):
    """'archived' when the latest event of a company closes its process (a closing event wins a tie on the day)."""
    if not rows:
        return 'active'
    latest = max(rows, key=lambda r: (r.date, r.type in CLOSING, r.time or '00:00'))
    return 'archived' if latest.type in CLOSING else 'active'


def downgrade():
    bind = op.get_bind()
    op.create_table(
        'agencies',
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
        sa.UniqueConstraint('name', name=op.f('uq_agencies_name')),
    )
    op.create_table(
        'agency_recruiters',
        sa.Column('agency_id', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], name=op.f('fk_agency_recruiters_agency_id_agencies'),
                                onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('agency_id', 'position', name=op.f('pk_agency_recruiters')),
    )
    op.create_table(
        'clients',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(collation='NOCASE'), nullable=False),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('linkedin', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), server_default='', nullable=False),
        sa.Column('via_agency_id', sa.String(), nullable=True),
        sa.CheckConstraint('length(trim(name)) > 0', name=op.f('ck_clients_name_not_blank')),
        sa.ForeignKeyConstraint(['via_agency_id'], ['agencies.id'], name=op.f('fk_clients_via_agency_id_agencies'),
                                onupdate='CASCADE', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_clients')),
        sa.UniqueConstraint('name', name=op.f('uq_clients_name')),
    )
    events = bind.execute(sa.text('SELECT company_id, via_company_id, date, time, type FROM events')).fetchall()
    for c in bind.execute(sa.text("SELECT id, name, notes, website, linkedin, application_link FROM companies WHERE company_type = 'agency'")).fetchall():
        mine = [e for e in events if c.id in (e.company_id, e.via_company_id)]
        bind.execute(sa.text('INSERT INTO agencies (id, name, type, website, linkedin, application_link, status) '
                             'VALUES (:id, :name, :type, :website, :linkedin, :application_link, :status)'),
                     dict(id=c.id, name=c.name, type=c.notes or '', website=c.website, linkedin=c.linkedin,
                          application_link=c.application_link, status=_status(mine)))
    bind.execute(sa.text('INSERT INTO agency_recruiters (agency_id, position, url) SELECT company_id, position, url FROM company_recruiters '
                         "WHERE company_id IN (SELECT id FROM companies WHERE company_type = 'agency')"))
    bind.execute(sa.text('INSERT INTO clients (id, name, website, linkedin, notes, via_agency_id) '
                         "SELECT id, name, website, linkedin, notes, via_company_id FROM companies WHERE company_type = 'client'"))

    _events_table('events_old', [
        sa.Column('agency_id', sa.String(), nullable=True),
        sa.Column('client_id', sa.String(), nullable=True),
    ], "type <> 'passive_message' OR agency_id IS NOT NULL OR client_id IS NOT NULL", [
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], name=op.f('fk_events_agency_id_agencies'), onupdate='CASCADE', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name=op.f('fk_events_client_id_clients'), onupdate='CASCADE', ondelete='RESTRICT'),
    ])
    columns = 'e.id, e.date, e.time, e.type, e.notes, e.jd_url, e.apply_type, e.calendar_event_id, e.created_at'
    names = 'id, date, time, type, notes, jd_url, apply_type, calendar_event_id, created_at'
    # an event of an agency; an event of a client keeps the agency it came through
    bind.execute(sa.text('INSERT INTO events_old (%s, agency_id, client_id) SELECT %s, e.company_id, NULL FROM events e '
                         "JOIN companies c ON c.id = e.company_id WHERE c.company_type = 'agency'" % (names, columns)))
    bind.execute(sa.text('INSERT INTO events_old (%s, agency_id, client_id) SELECT %s, e.via_company_id, e.company_id FROM events e '
                         "JOIN companies c ON c.id = e.company_id WHERE c.company_type = 'client'" % (names, columns)))
    bind.execute(sa.text('INSERT INTO events_old (%s, agency_id, client_id) SELECT %s, NULL, NULL FROM events e WHERE e.company_id IS NULL' % (names, columns)))
    op.drop_table('events')
    op.rename_table('events_old', 'events')
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_events_agency_id'), ['agency_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_events_client_id'), ['client_id'], unique=False)
    op.drop_table('company_recruiters')
    op.drop_table('companies')

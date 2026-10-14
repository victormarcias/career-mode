"""The rules the database itself enforces, whatever program writes to it."""
import pytest
from sqlalchemy.exc import IntegrityError


@pytest.fixture(autouse=True)
def base_rows(sql):
    sql("INSERT INTO agencies (id, name) VALUES ('acme', 'Acme')")
    sql("INSERT INTO clients (id, name, via_agency_id) VALUES ('big', 'Big', 'acme')")


def event(sql, **cols):
    cols = {'id': 'e1', 'date': '2026-10-08', 'type': 'note', **cols}
    sql('INSERT INTO events (%s) VALUES (%s)' % (', '.join(cols), ', '.join(':' + c for c in cols)), **cols)


def test_company_names_are_unique_ignoring_case(sql):
    with pytest.raises(IntegrityError):
        sql("INSERT INTO agencies (id, name) VALUES ('acme-2', 'ACME')")
    with pytest.raises(IntegrityError):
        sql("INSERT INTO clients (id, name) VALUES ('big-2', 'big')")


def test_blank_names_are_refused(sql):
    with pytest.raises(IntegrityError):
        sql("INSERT INTO agencies (id, name) VALUES ('x', '   ')")


def test_an_event_must_point_to_real_companies(sql):
    with pytest.raises(IntegrityError):
        event(sql, agency_id='ghost')
    with pytest.raises(IntegrityError):
        event(sql, client_id='ghost')
    event(sql, agency_id='acme', client_id='big')


@pytest.mark.parametrize('bad', [{'type': 'party'}, {'date': '08/10/2026'}, {'time': '9am'}, {'apply_type': 'carrier_pigeon'}, {'type': 'agency'}])
def test_event_types_dates_times_and_apply_types_are_checked(sql, bad):
    with pytest.raises(IntegrityError):
        event(sql, **bad)


def test_valid_values_are_accepted(sql):
    event(sql, time='09:30', apply_type='web_form')


def test_a_passive_message_needs_an_agency(sql):
    with pytest.raises(IntegrityError):
        event(sql, type='passive_message')
    with pytest.raises(IntegrityError):
        event(sql, type='passive_message', client_id='big')  # a client alone is not enough
    event(sql, type='passive_message', agency_id='acme')


def test_a_company_with_events_cannot_be_deleted(sql):
    event(sql, agency_id='acme', client_id='big')
    with pytest.raises(IntegrityError):
        sql("DELETE FROM agencies WHERE id = 'acme'")
    with pytest.raises(IntegrityError):
        sql("DELETE FROM clients WHERE id = 'big'")


def test_deleting_an_agency_without_events_frees_its_clients_and_recruiters(sql):
    sql("INSERT INTO agency_recruiters VALUES ('acme', 0, 'https://linkedin.com/in/x')")
    sql("DELETE FROM agencies WHERE id = 'acme'")
    assert sql("SELECT via_agency_id FROM clients WHERE id = 'big'").scalar() is None
    assert sql('SELECT COUNT(*) FROM agency_recruiters').scalar() == 0


def test_changing_an_id_follows_through(sql):
    event(sql, agency_id='acme')
    sql("UPDATE agencies SET id = 'acme-inc' WHERE id = 'acme'")
    assert sql('SELECT agency_id FROM events').scalar() == 'acme-inc'
    assert sql('SELECT via_agency_id FROM clients').scalar() == 'acme-inc'


def test_calendar_event_id_is_unique_when_set(sql):
    event(sql, id='a', calendar_event_id='g1')
    event(sql, id='b')
    event(sql, id='c')  # several NULLs are fine
    with pytest.raises(IntegrityError):
        event(sql, id='d', calendar_event_id='g1')

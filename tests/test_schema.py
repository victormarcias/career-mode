"""The rules the database itself enforces, whatever program writes to it."""
import pytest
from sqlalchemy.exc import IntegrityError


@pytest.fixture(autouse=True)
def base_rows(sql):
    sql("INSERT INTO companies (id, name, company_type) VALUES ('acme', 'Acme', 'agency')")
    sql("INSERT INTO companies (id, name, company_type, via_company_id) VALUES ('big', 'Big', 'client', 'acme')")


def event(sql, **cols):
    cols = {'id': 'e1', 'date': '2026-10-08', 'type': 'note', **cols}
    sql('INSERT INTO events (%s) VALUES (%s)' % (', '.join(cols), ', '.join(':' + c for c in cols)), **cols)


def test_company_names_are_unique_ignoring_case_whatever_the_type(sql):
    with pytest.raises(IntegrityError):
        sql("INSERT INTO companies (id, name, company_type) VALUES ('acme-2', 'ACME', 'agency')")
    with pytest.raises(IntegrityError):
        sql("INSERT INTO companies (id, name, company_type) VALUES ('acme-3', 'acme', 'client')")  # an agency's name, as a client


def test_blank_names_are_refused(sql):
    with pytest.raises(IntegrityError):
        sql("INSERT INTO companies (id, name, company_type) VALUES ('x', '   ', 'agency')")


def test_a_company_is_an_agency_or_a_client(sql):
    with pytest.raises(IntegrityError):
        sql("INSERT INTO companies (id, name, company_type) VALUES ('x', 'X', 'employer')")
    with pytest.raises(IntegrityError):
        sql("INSERT INTO companies (id, name, company_type) VALUES ('y', 'Y', NULL)")


def test_only_a_client_has_a_via(sql):
    with pytest.raises(IntegrityError):
        sql("INSERT INTO companies (id, name, company_type, via_company_id) VALUES ('z', 'Z', 'agency', 'acme')")
    with pytest.raises(IntegrityError):
        sql("UPDATE companies SET via_company_id = 'acme' WHERE id = 'acme'")


def test_an_event_must_point_to_real_companies(sql):
    with pytest.raises(IntegrityError):
        event(sql, company_id='ghost')
    with pytest.raises(IntegrityError):
        event(sql, company_id='big', via_company_id='ghost')
    event(sql, company_id='big', via_company_id='acme')


def test_a_via_needs_a_company(sql):
    with pytest.raises(IntegrityError):
        event(sql, via_company_id='acme')


@pytest.mark.parametrize('bad', [{'type': 'party'}, {'date': '08/10/2026'}, {'time': '9am'}, {'apply_type': 'carrier_pigeon'}, {'type': 'agency'}])
def test_event_types_dates_times_and_apply_types_are_checked(sql, bad):
    with pytest.raises(IntegrityError):
        event(sql, **bad)


def test_valid_values_are_accepted(sql):
    event(sql, time='09:30', apply_type='web_form')


def test_a_passive_message_needs_a_company(sql):
    with pytest.raises(IntegrityError):
        event(sql, type='passive_message')
    event(sql, type='passive_message', company_id='big')  # a company that hires directly has no agency
    event(sql, id='e2', type='passive_message', company_id='acme')


def test_a_company_with_events_cannot_be_deleted(sql):
    event(sql, company_id='big', via_company_id='acme')
    with pytest.raises(IntegrityError):
        sql("DELETE FROM companies WHERE id = 'acme'")  # its client's event came through it
    with pytest.raises(IntegrityError):
        sql("DELETE FROM companies WHERE id = 'big'")


def test_deleting_an_agency_without_events_frees_its_clients_and_recruiters(sql):
    sql("INSERT INTO company_recruiters VALUES ('acme', 0, 'https://linkedin.com/in/x')")
    sql("DELETE FROM companies WHERE id = 'acme'")
    assert sql("SELECT via_company_id FROM companies WHERE id = 'big'").scalar() is None
    assert sql('SELECT COUNT(*) FROM company_recruiters').scalar() == 0


def test_changing_an_id_follows_through(sql):
    event(sql, company_id='big', via_company_id='acme')
    sql("UPDATE companies SET id = 'acme-inc' WHERE id = 'acme'")
    assert sql('SELECT via_company_id FROM events').scalar() == 'acme-inc'
    assert sql("SELECT via_company_id FROM companies WHERE id = 'big'").scalar() == 'acme-inc'


def test_calendar_event_id_is_unique_when_set(sql):
    event(sql, id='a', calendar_event_id='g1')
    event(sql, id='b')
    event(sql, id='c')  # several NULLs are fine
    with pytest.raises(IntegrityError):
        event(sql, id='d', calendar_event_id='g1')

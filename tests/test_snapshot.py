"""Export, import, and loading the old Firestore backups."""
import pytest

from app import snapshot
from app.database import make_engine, migrate, session_factory


@pytest.fixture
def session(tmp_path):
    path = tmp_path / 'snap.db'
    migrate(path)
    engine = make_engine(path)
    with session_factory(engine)() as s:
        yield s
    engine.dispose()


def test_export_then_import_into_an_empty_database_gives_the_same_data(client, make_agency, make_client, make_event, session):
    make_agency('Acme', recruiters=['https://x'])
    make_client('Big', viaAgencyId='acme')
    make_event(agencyId='acme', clientId='big', event='rejection', notes='n')
    make_event(event='pending', jdUrl='https://p')
    exported = client.get('/api/export').json()
    report = snapshot.import_snapshot(session, exported, replace=True)
    assert (report['agencies'], report['clients'], report['events'], report['skipped']) == (1, 1, 2, [])
    assert snapshot.export_snapshot(session) == exported


def test_import_cuts_dangling_references_and_skips_what_it_cannot_load(session):
    data = {
        'agencies': [{'id': 'a', 'name': 'A', 'status': None, 'recruiters': None}, {'id': 'a2', 'name': 'a'}],
        'clients': [{'id': 'c', 'name': 'C', 'viaAgencyId': 'ghost'}],
        'applications': [  # the old Firestore name for events
            {'id': 'e1', 'date': '2026-10-01', 'event': 'note', 'agencyId': 'ghost', 'companyLabel': 'Ghost'},
            {'id': 'e2', 'date': '2026-10-02', 'event': 'passive_message', 'agencyId': 'ghost'},
            {'id': 'e3', 'date': '2026-10-03', 'event': 'party'},
            {'id': 'e4', 'date': '2026-10-04', 'event': 'note', 'time': ''},
        ],
    }
    report = snapshot.import_snapshot(session, data)
    assert (report['agencies'], report['clients'], report['events']) == (1, 1, 2)
    assert len(report['skipped']) == 3   # the duplicate name, the passive message left with no agency, the unknown type
    assert len(report['warnings']) == 3  # the ghost agency on the client, on e1 and on e2
    exported = snapshot.export_snapshot(session)
    assert exported['clients'][0]['viaAgencyId'] is None and exported['agencies'][0]['status'] == 'active'


def test_importing_twice_skips_what_is_already_there(session):
    data = {'agencies': [{'id': 'a', 'name': 'A'}], 'events': [{'id': 'e', 'date': '2026-10-01', 'event': 'note'}]}
    assert snapshot.import_snapshot(session, data)['agencies'] == 1
    second = snapshot.import_snapshot(session, data)
    assert (second['agencies'], second['events'], len(second['skipped'])) == (0, 0, 2)


def test_history_is_loaded_as_it_was_while_live_events_change_statuses(session):
    data = {'agencies': [{'id': 'a', 'name': 'A', 'status': 'active'}],
            'events': [{'id': 'e', 'date': '2026-10-01', 'event': 'rejection', 'agencyId': 'a'}]}
    snapshot.import_snapshot(session, data)
    assert snapshot.export_snapshot(session)['agencies'][0]['status'] == 'active'  # the import didn't re-derive it


def test_csv_export_is_two_files_and_loads_back_the_same_data(client, make_agency, make_client, make_event, session):
    make_agency('Acme', recruiters=['https://x/1', 'https://x/2'], applicationLink='a@b.co')
    make_client('Big', viaAgencyId='acme', notes='line one\nline two, with "quotes"')
    make_client('Solo')
    make_event(agencyId='acme', clientId='big', event='rejection', notes='=HYPERLINK("http://evil")')
    make_event(clientId='solo', event='note', notes="'+1 already quoted")
    make_event(event='pending', jdUrl='https://p')
    exported = client.get('/api/export').json()
    snapshot.import_snapshot(session, exported)  # `session` is a second, empty database
    files = snapshot.export_csv(session)
    assert set(files) == {'calendar', 'companies'}
    assert files['calendar'].splitlines()[0].startswith('id,date,time,event,company,')
    assert files['companies'].splitlines()[0].startswith('kind,id,name,')
    assert "'=HYPERLINK" in files['calendar']  # a spreadsheet must not run it

    parsed, warnings = snapshot.parse_csv(files['calendar'], files['companies'])
    assert warnings == []
    snapshot.import_snapshot(session, parsed, replace=True)
    assert snapshot.export_snapshot(session) == exported


def test_csv_import_tolerates_excel_bom_and_crlf_and_reports_bad_rows():
    companies = '﻿kind,id,name\r\nagency,a,A\r\nclient,c,C\r\nvendor,v,V\r\n'
    parsed, warnings = snapshot.parse_csv(None, companies)
    assert [a['id'] for a in parsed['agencies']] == ['a'] and [c['id'] for c in parsed['clients']] == ['c']
    assert len(warnings) == 1 and 'line 4' in warnings[0]
    with pytest.raises(ValueError):
        snapshot.parse_csv('nothing,useful\n1,2\n')

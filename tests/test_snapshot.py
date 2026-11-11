"""Export, import, and loading the older backups."""
import pytest

from app import snapshot
from app.database import create_schema, make_engine, session_factory


@pytest.fixture
def session(tmp_path):
    path = tmp_path / 'snap.db'
    create_schema(path)
    engine = make_engine(path)
    with session_factory(engine)() as s:
        yield s
    engine.dispose()


def test_export_then_import_into_an_empty_database_gives_the_same_data(client, make_agency, make_client, make_event, session):
    make_agency('Acme', recruiters=['https://x'])
    make_client('Big', viaCompanyId='acme')
    # Each event on its own day: on the same day the order falls back to `created_at`, which a backup doesn't keep
    make_event(companyId='big', viaCompanyId='acme', event='rejection', notes='n', date='2026-10-01')
    make_event(event='pending', jdUrl='https://p', date='2026-10-02')
    exported = client.get('/api/export').json()
    report = snapshot.import_snapshot(session, exported, replace=True)
    assert (report['companies'], report['events'], report['skipped']) == (2, 2, [])
    assert snapshot.export_snapshot(session) == exported


def test_import_cuts_dangling_references_and_skips_what_it_cannot_load(session):
    data = {
        'companies': [
            {'id': 'a', 'name': 'A', 'companyType': 'agency', 'recruiters': None},
            {'id': 'a2', 'name': 'a', 'companyType': 'client'},  # the same name
            {'id': 'c', 'name': 'C', 'companyType': 'client', 'viaCompanyId': 'ghost'},
        ],
        'events': [
            {'id': 'e1', 'date': '2026-10-01', 'event': 'note', 'companyId': 'ghost'},
            {'id': 'e2', 'date': '2026-10-02', 'event': 'passive_message', 'companyId': 'ghost'},
            {'id': 'e3', 'date': '2026-10-03', 'event': 'party'},
            {'id': 'e4', 'date': '2026-10-04', 'event': 'note', 'time': ''},
        ],
    }
    report = snapshot.import_snapshot(session, data)
    assert (report['companies'], report['events']) == (2, 2)
    assert len(report['skipped']) == 3   # the duplicate name, the passive message left with no company, the unknown type
    assert len(report['warnings']) == 3  # the ghost agency on the client, the ghost company on e1 and on e2
    exported = snapshot.export_snapshot(session)
    assert [c['viaCompanyId'] for c in exported['companies']] == [None, None]


def test_importing_twice_skips_what_is_already_there(session):
    data = {'companies': [{'id': 'a', 'name': 'A', 'companyType': 'agency'}], 'events': [{'id': 'e', 'date': '2026-10-01', 'event': 'note'}]}
    assert snapshot.import_snapshot(session, data)['companies'] == 1
    second = snapshot.import_snapshot(session, data)
    assert (second['companies'], second['events'], len(second['skipped'])) == (0, 0, 2)


def test_csv_export_is_two_files_and_loads_back_the_same_data(client, make_agency, make_client, make_event, session):
    make_agency('Acme', recruiters=['https://x/1', 'https://x/2'], applicationLink='a@b.co')
    make_client('Big', viaCompanyId='acme', notes='line one\nline two, with "quotes"')
    make_client('Solo')
    make_event(companyId='big', viaCompanyId='acme', event='rejection', notes='=HYPERLINK("http://evil")', date='2026-10-01')
    make_event(companyId='solo', event='note', notes="'+1 already quoted", date='2026-10-02')
    make_event(event='pending', jdUrl='https://p', date='2026-10-03')
    exported = client.get('/api/export').json()
    snapshot.import_snapshot(session, exported)  # `session` is a second, empty database
    files = snapshot.export_csv(session)
    assert set(files) == {'calendar', 'companies'}
    assert files['calendar'].splitlines()[0].startswith('id,date,time,event,company,')
    assert files['companies'].splitlines()[0].startswith('company_type,id,name,')
    assert "'=HYPERLINK" in files['calendar']  # a spreadsheet must not run it

    parsed, warnings = snapshot.parse_csv(files['calendar'], files['companies'])
    assert warnings == []
    snapshot.import_snapshot(session, parsed, replace=True)
    assert snapshot.export_snapshot(session) == exported


def test_csv_import_tolerates_excel_bom_and_crlf_and_reports_bad_rows():
    companies = '\ufeffcompany_type,id,name\r\nagency,a,A\r\nclient,c,C\r\nvendor,v,V\r\n'
    parsed, warnings = snapshot.parse_csv(None, companies)
    assert [c['id'] for c in parsed['companies']] == ['a', 'c']
    assert len(warnings) == 1 and 'line 4' in warnings[0]
    with pytest.raises(ValueError):
        snapshot.parse_csv('nothing,useful\n1,2\n')


def test_a_companies_file_without_company_type_is_refused_once_not_row_by_row():
    old = 'kind,id,name\nagency,acme,Acme\nclient,beta,Beta\n'  # the column an older export called it
    with pytest.raises(ValueError, match='company_type'):
        snapshot.parse_csv(None, old)

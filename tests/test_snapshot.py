"""Export, import, and loading the older backups."""
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
    make_client('Big', viaCompanyId='acme')
    make_event(companyId='big', viaCompanyId='acme', event='rejection', notes='n')
    make_event(event='pending', jdUrl='https://p')
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


def test_the_older_backups_of_agencies_and_clients_still_load(session):
    """Agencies and clients as two lists (and the Firestore `applications`): they become companies, and an event of a client
    keeps its agency as the via. An agency and a client that shared an id or a name no longer can."""
    data = {
        'agencies': [{'id': 'acme', 'name': 'Acme', 'type': 'staffing', 'status': 'archived', 'recruiters': ['https://x']}],
        'clients': [
            {'id': 'big', 'name': 'Big', 'notes': 'a client', 'viaAgencyId': 'acme'},
            {'id': 'acme', 'name': 'ACME'},  # the same id and name as the agency
        ],
        'applications': [
            {'id': 'e1', 'date': '2026-10-01', 'event': 'rejection', 'agencyId': 'acme', 'clientId': 'big', 'companyLabel': 'Acme'},
            {'id': 'e2', 'date': '2026-10-02', 'event': 'note', 'agencyId': 'acme'},
            {'id': 'e3', 'date': '2026-10-03', 'event': 'note', 'clientId': 'acme'},
        ],
    }
    report = snapshot.import_snapshot(session, data)
    assert (report['companies'], report['events'], report['skipped']) == (3, 3, [])
    exported = snapshot.export_snapshot(session)
    companies = {c['id']: c for c in exported['companies']}
    assert (companies['acme']['companyType'], companies['acme']['notes'], companies['acme']['recruiters']) == ('agency', 'staffing', ['https://x'])
    assert (companies['big']['companyType'], companies['big']['viaCompanyId']) == ('client', 'acme')
    assert (companies['acme-2']['companyType'], companies['acme-2']['name']) == ('client', 'ACME (client)')
    events = {e['id']: (e['companyId'], e['viaCompanyId']) for e in exported['events']}
    assert events == {'e1': ('big', 'acme'), 'e2': ('acme', None), 'e3': ('acme-2', None)}


def test_csv_export_is_two_files_and_loads_back_the_same_data(client, make_agency, make_client, make_event, session):
    make_agency('Acme', recruiters=['https://x/1', 'https://x/2'], applicationLink='a@b.co')
    make_client('Big', viaCompanyId='acme', notes='line one\nline two, with "quotes"')
    make_client('Solo')
    make_event(companyId='big', viaCompanyId='acme', event='rejection', notes='=HYPERLINK("http://evil")')
    make_event(companyId='solo', event='note', notes="'+1 already quoted")
    make_event(event='pending', jdUrl='https://p')
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


def test_the_older_csv_files_load_too():
    companies = 'kind,id,name,type,via_agency_id\nagency,a,A,staffing,\nclient,c,C,,a\n'
    calendar = 'id,date,event,agency_id,client_id\ne1,2026-10-01,note,a,c\ne2,2026-10-02,note,a,\n'
    parsed, warnings = snapshot.parse_csv(calendar, companies)
    assert warnings == []
    assert [(c['id'], c['companyType'], c['notes'], c['viaCompanyId']) for c in parsed['companies']] == [('a', 'agency', 'staffing', None), ('c', 'client', None, 'a')]
    assert [(e['id'], e['agencyId'], e['clientId']) for e in parsed['events']] == [('e1', 'a', 'c'), ('e2', 'a', None)]  # import_snapshot turns them into company and via


def test_csv_import_tolerates_excel_bom_and_crlf_and_reports_bad_rows():
    companies = '\ufeffcompany_type,id,name\r\nagency,a,A\r\nclient,c,C\r\nvendor,v,V\r\n'
    parsed, warnings = snapshot.parse_csv(None, companies)
    assert [c['id'] for c in parsed['companies']] == ['a', 'c']
    assert len(warnings) == 1 and 'line 4' in warnings[0]
    with pytest.raises(ValueError):
        snapshot.parse_csv('nothing,useful\n1,2\n')

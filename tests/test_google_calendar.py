"""Google Calendar sync: the iCal reading, what gets logged, and the route. Nothing here reaches Google."""
import datetime as dt
import ssl
from urllib.error import URLError
from zoneinfo import ZoneInfo

import pytest

from app import google_calendar
from app.crud import DomainError

LOCAL = ZoneInfo('America/Sao_Paulo')  # UTC-3, no daylight saving
MON, FRI = dt.date(2026, 10, 12), dt.date(2026, 10, 16)


def vevent(**props):
    return 'BEGIN:VEVENT\r\n' + ''.join('%s:%s\r\n' % (k.replace('_', '-'), v) for k, v in props.items()) + 'END:VEVENT\r\n'


def calendar(*events):
    return 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\n' + ''.join(events) + 'END:VCALENDAR\r\n'


# a Calendly booking: UTC time, and the company on its own line of the description
CALENDLY = vevent(
    UID='cal1@google.com', DTSTART='20261013T180000Z', SUMMARY='HR intro with Acme', DESCRIPTION='Company: Acme\\nPhone: 1',
)


def test_a_utc_time_is_read_in_the_given_zone():
    [event] = google_calendar.parse_ics(calendar(CALENDLY), LOCAL)
    assert (event.key, event.summary) == ('cal1@google.com', 'HR intro with Acme')
    assert event.start == dt.datetime(2026, 10, 13, 15, 0, tzinfo=LOCAL)  # 18:00Z is 15:00 in São Paulo
    assert event.description == 'Company: Acme\nPhone: 1'  # \n in iCal is a line break


def test_a_time_with_its_own_zone_is_converted():
    ics = calendar('BEGIN:VEVENT\r\nUID:a\r\nDTSTART;TZID=America/New_York:20261013T140000\r\nSUMMARY:x\r\nEND:VEVENT\r\n')
    [event] = google_calendar.parse_ics(ics, LOCAL)
    assert event.start == dt.datetime(2026, 10, 13, 15, 0, tzinfo=LOCAL)  # 14:00 in New York (UTC-4) is 15:00 in São Paulo


def test_a_folded_and_escaped_line_is_put_back_together():
    ics = calendar('BEGIN:VEVENT\r\nUID:a\r\nDTSTART:20261013T180000Z\r\nSUMMARY:Intro\\, with a very long\r\n  title\r\nEND:VEVENT\r\n')
    [event] = google_calendar.parse_ics(ics, LOCAL)
    assert event.summary == 'Intro, with a very long title'


def test_an_occurrence_of_a_repeating_event_has_its_own_key():
    ics = calendar(vevent(UID='r', DTSTART='20261013T180000Z', RECURRENCE_ID='20261006T180000Z'))
    assert google_calendar.parse_ics(ics, LOCAL)[0].key == 'r|20261006T180000Z'


def logged(client):
    return {e['calendarEventId']: e for e in client.get('/api/events').json()}


def feed(client, env_path, *events):
    env_path.write_text('GOOGLE_CALENDAR_ID=me@example.com\n')
    client.app.state.fetch_ics = lambda url: calendar(*events)


def body(first=MON, last=FRI, **extra):
    return {'start': first.isoformat(), 'end': last.isoformat(), **extra}


def preview(client, env_path, *events, **kw):
    feed(client, env_path, *events)
    return client.post('/api/calendar/preview', json=body(**kw))


def sync(client, env_path, *events, types=None, companies=None, **kw):
    """Previews, then confirms what the preview listed, as the type and the company it offered (unless told another)."""
    listed = preview(client, env_path, *events, **kw).json()['events']
    chosen = []
    for e in listed:
        company, company_type, via = (companies or {}).get(e['key'], (e['company'], e['companyType'], e['via']))
        chosen.append({'key': e['key'], 'type': (types or {}).get(e['key'], e['type']), 'company': company, 'companyType': company_type, 'via': via})
    return client.post('/api/calendar/sync', json=body(events=chosen, **kw))


def test_it_refuses_without_a_calendar_id(client):
    for route in ('preview', 'sync'):
        r = client.post('/api/calendar/%s' % route, json=body(events=[]))
        assert r.status_code == 409 and 'Settings' in r.json()['detail']


def test_the_preview_lists_what_would_be_added_and_adds_nothing(client, env_path):
    client.post('/api/companies', json={'name': 'Acme', 'companyType': 'agency'})
    r = preview(client, env_path, CALENDLY)
    assert r.status_code == 200
    [event] = r.json()['events']
    assert event == {
        'key': 'cal1@google.com', 'summary': 'HR intro with Acme', 'notes': 'HR intro with Acme\n\nCompany: Acme\nPhone: 1',
        'date': '2026-10-13', 'time': event['time'], 'company': 'Acme', 'companyType': 'agency', 'via': None, 'action': 'new', 'type': 'hr_intro',
    }
    assert (r.json()['unchanged'], r.json()['recurringSkipped']) == (0, 0)
    assert client.get('/api/events').json() == []


def test_tech_in_the_title_suggests_a_tech_interview_and_cultur_a_culture_one(client, env_path):
    events = [
        vevent(UID='a', DTSTART='20261013T180000Z', SUMMARY='Tech interview - Acme'),
        vevent(UID='b', DTSTART='20261013T190000Z', SUMMARY='Technical screen'),
        vevent(UID='c', DTSTART='20261013T200000Z', SUMMARY='TECH chat'),
        vevent(UID='d', DTSTART='20261013T210000Z', SUMMARY='Intro with Acme'),
        vevent(UID='e', DTSTART='20261013T220000Z', SUMMARY='Culture fit with Acme'),
        vevent(UID='f', DTSTART='20261014T130000Z', SUMMARY='Cultural interview'),
    ]
    types = {e['key']: e['type'] for e in preview(client, env_path, *events).json()['events']}
    assert types == {
        'a': 'tech_interview', 'b': 'tech_interview', 'c': 'tech_interview', 'd': 'hr_intro',
        'e': 'culture_interview', 'f': 'culture_interview',
    }


def test_a_culture_interview_can_be_logged_from_the_calendar(client, env_path):
    feed(client, env_path, CALENDLY)
    r = client.post('/api/calendar/sync', json=body(events=[{'key': 'cal1@google.com', 'type': 'culture_interview', 'company': 'Acme'}]))
    assert r.status_code == 200 and r.json()['created'] == 1
    assert logged(client)['cal1@google.com']['event'] == 'culture_interview'


def test_the_title_and_the_description_go_to_the_notes(client, env_path):
    client.post('/api/companies', json={'name': 'Acme', 'companyType': 'agency'})
    r = sync(client, env_path, CALENDLY, types={'cal1@google.com': 'tech_interview'})
    assert r.status_code == 200 and r.json() == {'created': 1, 'updated': 0}
    event = logged(client)['cal1@google.com']
    assert (event['event'], event['companyId'], event['companyLabel']) == ('tech_interview', 'acme', 'Acme')
    assert event['notes'] == 'HR intro with Acme\n\nCompany: Acme\nPhone: 1'
    assert event['date'] == '2026-10-13' and len(event['time']) == 5


def test_an_event_with_no_description_has_just_its_title_as_notes(client, env_path):
    sync(client, env_path, vevent(UID='a', DTSTART='20261013T180000Z', SUMMARY='Intro'), companies={'a': ('Acme', 'agency', None)})
    assert logged(client)['a']['notes'] == 'Intro'


def test_a_description_in_html_becomes_plain_text(client, env_path):
    html = 'Call at 3<br>Link: <a href="https://meet.google.com/abc">https://meet.google.com/abc</a><br><br><br>See <a href="https://acme.com">our site</a> &amp; more &lt;3'
    assert google_calendar.clean_description(html) == 'Call at 3\nLink: https://meet.google.com/abc\n\nSee [our site](https://acme.com) & more <3'
    assert google_calendar.clean_description('a < b and c > d') == 'a < b and c > d'


def test_the_first_event_of_a_company_creates_it(client, env_path):
    assert client.get('/api/companies').json() == []
    r = sync(client, env_path, CALENDLY)  # the preview offers "Acme" as an agency the app does not have
    assert r.json() == {'created': 1, 'updated': 0}
    [company] = client.get('/api/companies').json()
    assert (company['name'], company['companyType'], company['status']) == ('Acme', 'agency', 'active')
    event = logged(client)['cal1@google.com']
    assert (event['companyId'], event['viaCompanyId'], event['companyLabel']) == (company['id'], None, 'Acme')


def test_two_events_of_a_new_company_create_it_once(client, env_path):
    events = [vevent(UID='a', DTSTART='20261013T180000Z', SUMMARY='one'), vevent(UID='b', DTSTART='20261014T180000Z', SUMMARY='two')]
    sync(client, env_path, *events, companies={'a': ('Newco', 'agency', None), 'b': ('newco', 'agency', None)})
    assert [a['name'] for a in client.get('/api/companies').json()] == ['Newco']
    assert {e['companyId'] for e in client.get('/api/events').json()} == {'newco'}


def test_a_new_direct_client_is_created_without_an_agency(client, env_path):
    sync(client, env_path, CALENDLY, companies={'cal1@google.com': ('Acme Inc', 'client', None)})
    [created] = client.get('/api/companies').json()
    assert (created['name'], created['companyType'], created['viaCompanyId']) == ('Acme Inc', 'client', None)
    assert logged(client)['cal1@google.com']['companyId'] == created['id']


def test_a_client_with_an_agency_is_linked_to_both(client, env_path):
    sync(client, env_path, CALENDLY, companies={'cal1@google.com': ('Acme', 'client', 'Staffing Co')})
    companies = {c['name']: c for c in client.get('/api/companies').json()}
    event = logged(client)['cal1@google.com']
    assert (companies['Acme']['companyType'], companies['Acme']['viaCompanyId'], companies['Staffing Co']['companyType']) == ('client', 'staffing-co', 'agency')
    assert (event['companyId'], event['viaCompanyId']) == ('acme', 'staffing-co')
    assert event['companyLabel'] == 'Staffing Co → Acme'


def test_a_known_client_alone_brings_its_agency_and_is_found_by_the_description(client, env_path):
    client.post('/api/companies', json={'name': 'Staffing Co', 'companyType': 'agency'})
    client.post('/api/companies', json={'name': 'Acme', 'companyType': 'client', 'viaCompanyId': 'staffing-co'})
    [offer] = preview(client, env_path, CALENDLY).json()['events']
    assert (offer['company'], offer['companyType'], offer['via']) == ('Acme', 'client', 'Staffing Co')  # the agency it came through
    sync(client, env_path, CALENDLY, companies={'cal1@google.com': ('acme', None, None)})
    event = logged(client)['cal1@google.com']
    assert (event['companyId'], event['viaCompanyId']) == ('acme', 'staffing-co')
    assert len(client.get('/api/companies').json()) == 2


def test_a_name_that_exists_as_the_other_type_is_refused_and_nothing_is_written(client, env_path):
    client.post('/api/companies', json={'name': 'Acme', 'companyType': 'agency'})
    r = sync(client, env_path, CALENDLY, companies={'cal1@google.com': ('Acme', 'client', None)})
    assert r.status_code == 409 and 'already an agency' in r.json()['detail']
    assert client.get('/api/events').json() == [] and len(client.get('/api/companies').json()) == 1
    r = sync(client, env_path, CALENDLY, companies={'cal1@google.com': ('Acme', 'agency', 'Other')})  # an agency has no agency
    assert r.status_code == 422 and len(client.get('/api/companies').json()) == 1


def test_an_event_needs_a_company_and_nothing_is_written_before_checking(client, env_path):
    events = [vevent(UID='a', DTSTART='20261013T180000Z', SUMMARY='one'), vevent(UID='b', DTSTART='20261014T180000Z', SUMMARY='two')]
    feed(client, env_path, *events)
    chosen = [{'key': 'a', 'type': 'hr_intro', 'company': 'Newco'}, {'key': 'b', 'type': 'hr_intro'}]
    r = client.post('/api/calendar/sync', json=body(events=chosen))
    assert r.status_code == 422 and '"two"' in r.json()['detail']
    assert client.get('/api/events').json() == [] and client.get('/api/companies').json() == []  # not even Newco


def test_an_event_without_a_company_line_offers_none(client, env_path):
    [offer] = preview(client, env_path, vevent(UID='a', DTSTART='20261013T180000Z', SUMMARY='Chat')).json()['events']
    assert (offer['company'], offer['companyType'], offer['via']) == (None, None, None)


def test_only_the_events_that_were_confirmed_are_logged(client, env_path):
    events = [vevent(UID='a', DTSTART='20261013T180000Z', SUMMARY='one'), vevent(UID='b', DTSTART='20261014T180000Z', SUMMARY='two')]
    feed(client, env_path, *events)
    r = client.post('/api/calendar/sync', json=body(events=[{'key': 'b', 'type': 'hr_intro', 'company': 'Acme'}]))
    assert r.json() == {'created': 1, 'updated': 0} and list(logged(client)) == ['b']
    assert [e['key'] for e in client.post('/api/calendar/preview', json=body()).json()['events']] == ['a']  # still offered


def test_a_type_that_is_not_an_interview_of_the_calendar_is_refused(client, env_path):
    feed(client, env_path, CALENDLY)
    r = client.post('/api/calendar/sync', json=body(events=[{'key': 'cal1@google.com', 'type': 'offer', 'company': 'Acme'}]))
    assert r.status_code == 422 and client.get('/api/events').json() == []


def test_a_logged_event_is_not_offered_again_and_a_moved_one_is_offered_as_moved(client, env_path):
    sync(client, env_path, CALENDLY)
    again = preview(client, env_path, CALENDLY).json()
    assert again['events'] == [] and again['unchanged'] == 1
    moved = vevent(UID='cal1@google.com', DTSTART='20261014T180000Z', SUMMARY='HR intro with Acme', DESCRIPTION='Company: Acme')
    [offer] = preview(client, env_path, moved).json()['events']
    assert (offer['action'], offer['date'], offer['company']) == ('moved', '2026-10-14', 'Acme')  # its own company
    assert sync(client, env_path, moved).json() == {'created': 0, 'updated': 1}
    assert logged(client)['cal1@google.com']['date'] == '2026-10-14' and len(client.get('/api/events').json()) == 1


def test_a_type_company_and_notes_changed_by_hand_are_kept_when_the_event_moves(client, env_path):
    sync(client, env_path, CALENDLY)
    event = logged(client)['cal1@google.com']
    client.post('/api/companies', json={'name': 'Other', 'companyType': 'agency'})
    client.patch('/api/events/%s' % event['id'], json={'event': 'tech_filter', 'notes': 'my notes', 'companyId': 'other'})
    moved = vevent(UID='cal1@google.com', DTSTART='20261014T180000Z', SUMMARY='HR intro with Acme', DESCRIPTION='Company: Acme')
    sync(client, env_path, moved, types={'cal1@google.com': 'hr_intro'}, companies={'cal1@google.com': ('Acme', 'agency', None)})
    kept = logged(client)['cal1@google.com']
    assert (kept['event'], kept['notes'], kept['companyId'], kept['date']) == ('tech_filter', 'my notes', 'other', '2026-10-14')


def test_only_the_asked_days_all_day_cancelled_and_repeating_events_are_left_out(client, env_path):
    events = [
        vevent(UID='outside', DTSTART='20261020T180000Z', SUMMARY='next week'),
        vevent(UID='allday', DTSTART='20261013', SUMMARY='holiday'),
        vevent(UID='gone', DTSTART='20261013T180000Z', SUMMARY='x', STATUS='CANCELLED'),
        vevent(UID='weekly', DTSTART='20260929T180000Z', SUMMARY='standup', RRULE='FREQ=WEEKLY'),
        vevent(UID='ended', DTSTART='20260901T180000Z', SUMMARY='old', RRULE='FREQ=WEEKLY;UNTIL=20260930T000000Z'),
        vevent(UID='in', DTSTART='20261015T190000Z', SUMMARY='kept'),
    ]
    plan = preview(client, env_path, *events).json()
    assert [e['key'] for e in plan['events']] == ['in'] and plan['recurringSkipped'] == 1
    assert sync(client, env_path, *events, companies={'in': ('Acme', 'agency', None)}).json() == {'created': 1, 'updated': 0}
    assert list(logged(client)) == ['in']


def test_the_end_cannot_be_before_the_start(client, env_path):
    assert preview(client, env_path, CALENDLY, first=FRI, last=MON).status_code == 422


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.text.encode()


def test_google_is_reached_with_certifis_certificates(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout, context):
        seen['context'] = context
        return FakeResponse(calendar(CALENDLY))

    monkeypatch.setattr(google_calendar, 'urlopen', fake_urlopen)
    assert 'BEGIN:VCALENDAR' in google_calendar.fetch_ics('https://calendar.google.com/x.ics')
    assert isinstance(seen['context'], ssl.SSLContext) and seen['context'].verify_mode == ssl.CERT_REQUIRED
    assert seen['context'].cert_store_stats()['x509_ca'] > 0  # certifi's list is loaded, so a Mac without its own works


def test_a_network_failure_is_a_sentence_not_a_crash(monkeypatch):
    def refuse(*args, **kwargs):
        raise URLError('boom')

    monkeypatch.setattr(google_calendar, 'urlopen', refuse)
    with pytest.raises(DomainError) as err:
        google_calendar.fetch_ics('https://calendar.google.com/x.ics')
    assert (err.value.status, 'boom' in err.value.message) == (502, True)


def test_the_end_cannot_be_before_the_start(client, env_path):
    assert preview(client, env_path, CALENDLY, first=FRI, last=MON).status_code == 422


def test_the_calendar_id_becomes_the_public_ical_address():
    assert google_calendar.ics_url('me@example.com') == 'https://calendar.google.com/calendar/ical/me@example.com/public/basic.ics'
    secret = 'https://calendar.google.com/calendar/ical/me%40example.com/private-abc/basic.ics'
    assert google_calendar.ics_url(secret) == secret


@pytest.mark.parametrize('bad', ['two words', 'http://calendar.google.com/x.ics', 'https://evil.example/x.ics',
                                 'https://calendar.google.com.evil.example/x.ics'])
def test_a_calendar_id_that_cannot_be_one_is_refused(client, bad):
    r = client.put('/api/settings/env', json={'values': {'GOOGLE_CALENDAR_ID': bad}})
    assert r.status_code == 422


def test_the_calendar_id_is_a_secret(client):
    client.put('/api/settings/env', json={'values': {'GOOGLE_CALENDAR_ID': 'me@example.com'}})
    row = {r['name']: r for r in client.get('/api/settings/env').json()}['GOOGLE_CALENDAR_ID']
    assert (row['isSet'], row['value'], row['secret'], row['length']) == (True, None, True, len('me@example.com'))
    assert 'me@example.com' not in client.get('/api/settings/env').text

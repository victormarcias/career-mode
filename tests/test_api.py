"""The JSON API: companies (agencies and clients) and events, through the real app (in-process)."""


# ---------- companies ----------


def test_a_name_that_exists_is_refused_ignoring_case_whatever_the_type(client, make_agency):
    make_agency('Acme')
    for company_type in ('agency', 'client'):  # the same name as a client is the duplicate the front end used to make
        r = client.post('/api/companies', json={'name': ' ACME ', 'companyType': company_type})
        assert r.status_code == 409
        assert 'already exists' in r.json()['detail']


def test_ids_never_collide(make_agency, make_client):
    make_agency('A.B')
    assert make_client('A B')['id'] == 'a-b-2'


def test_clients_via_agency_and_direct(client, make_agency, make_client):
    make_agency('Acme')
    via, direct = make_client('Big', viaCompanyId='acme'), make_client('Direct Co')
    assert (via['viaCompanyId'], direct['viaCompanyId']) == ('acme', None)
    assert client.patch('/api/companies/big', json={'viaCompanyId': None}).json()['viaCompanyId'] is None
    assert client.patch('/api/companies/big', json={'viaCompanyId': 'ghost'}).status_code == 422


def test_the_type_can_be_changed_unless_the_agency_is_still_in_use(client, make_agency, make_client, make_event):
    make_agency('Oowlish')
    assert client.patch('/api/companies/oowlish', json={'companyType': 'client'}).json()['companyType'] == 'client'  # an employer logged as an agency
    make_agency('Acme')
    make_client('Big', viaCompanyId='acme')
    r = client.patch('/api/companies/acme', json={'companyType': 'client'})
    assert r.status_code == 409 and '1 client' in r.json()['detail']
    body = client.patch('/api/companies/big', json={'companyType': 'agency'}).json()
    assert (body['companyType'], body['viaCompanyId']) == ('agency', None)  # an agency has no via: it is dropped
    make_event(companyId='big', viaCompanyId=None)


def test_a_client_whose_events_came_through_an_agency_cannot_become_an_agency(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Big', viaCompanyId='acme')
    make_event(companyId='big', viaCompanyId='acme')
    r = client.patch('/api/companies/big', json={'companyType': 'agency'})
    assert r.status_code == 409 and '1 event that came through an agency' in r.json()['detail']
    r = client.put('/api/companies/big', json={'name': 'Big', 'companyType': 'agency'})
    assert r.status_code == 409
    assert client.get('/api/companies/big').json()['companyType'] == 'client'  # nothing changed
    assert client.delete('/api/companies/acme').status_code == 409  # Acme still brought that process


def test_deleting_a_company_that_still_has_events_is_refused_with_the_count(client, make_agency, make_event):
    make_agency('Acme')
    make_event(companyId='acme')
    make_event(companyId='acme')
    r = client.delete('/api/companies/acme')
    assert r.status_code == 409 and '2 events' in r.json()['detail']
    assert client.get('/api/companies/acme').status_code == 200


def test_an_agency_cannot_be_deleted_while_its_clients_have_events_through_it(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Big', viaCompanyId='acme')
    make_event(companyId='big', viaCompanyId='acme')
    assert client.delete('/api/companies/acme').status_code == 409


def test_deleting_an_agency_without_events_makes_its_clients_direct(client, make_agency, make_client):
    make_agency('Acme')
    make_client('Big', viaCompanyId='acme')
    assert client.delete('/api/companies/acme').status_code == 204
    assert client.get('/api/companies/big').json()['viaCompanyId'] is None


def test_company_label_is_derived_from_the_links(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Big')
    make_client('Direct Co')
    assert make_event(companyId='acme')['companyLabel'] == 'Acme'
    assert make_event(companyId='big', viaCompanyId='acme')['companyLabel'] == 'Acme → Big'
    assert make_event(companyId='direct-co')['companyLabel'] == 'Direct Co'
    assert make_event(event='pending', jdUrl='https://x')['companyLabel'] == '—'
    client.patch('/api/companies/acme', json={'name': 'Acme Inc'})
    labels = {e['companyLabel'] for e in client.get('/api/events', params={'companyId': 'acme'}).json()}
    assert labels == {'Acme Inc', 'Acme Inc → Big'}  # follows a rename


def test_event_validation(client, make_agency, make_client):
    make_agency('Acme')
    make_client('Big')
    bad = [
        {'date': '2026-13-45', 'event': 'note'},
        {'date': '2026-10-08', 'event': 'party'},
        {'date': '2026-10-08', 'event': 'note', 'time': '25:00'},
        {'date': '2026-10-08', 'event': 'note', 'companyId': 'ghost'},
        {'date': '2026-10-08', 'event': 'note', 'companyId': 'big', 'viaCompanyId': 'ghost'},
        {'date': '2026-10-08', 'event': 'note', 'companyId': 'big', 'viaCompanyId': 'big'},      # a via is an agency
        {'date': '2026-10-08', 'event': 'note', 'companyId': 'acme', 'viaCompanyId': 'acme'},    # only a client's event has one
        {'date': '2026-10-08', 'event': 'note', 'viaCompanyId': 'acme'},                         # and it needs its company
        {'date': '2026-10-08', 'event': 'application', 'applyType': 'pigeon'},
        {'event': 'note'},
    ]
    for body in bad:
        assert client.post('/api/events', json=body).status_code == 422, body


def test_a_patch_checks_the_links_with_the_ones_the_event_already_has(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_agency('Other Agency')
    make_client('Big')
    e = make_event(companyId='big')
    r = client.patch('/api/events/' + e['id'], json={'viaCompanyId': 'acme'})  # its company, a client, is not sent
    assert r.status_code == 200, r.text
    assert (r.json()['companyId'], r.json()['viaCompanyId']) == ('big', 'acme')
    assert client.patch('/api/events/' + e['id'], json={'viaCompanyId': 'big'}).status_code == 422  # still not an agency
    agency_event = make_event(companyId='acme')
    assert client.patch('/api/events/' + agency_event['id'], json={'viaCompanyId': 'other-agency'}).status_code == 422


def test_the_agency_an_event_had_goes_when_its_company_is_no_longer_a_client(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_agency('Other Agency')
    make_client('Big')
    make_client('Small')
    e = make_event(companyId='big', viaCompanyId='acme')
    moved = client.patch('/api/events/' + e['id'], json={'companyId': 'small'}).json()  # to another client: kept
    assert (moved['companyId'], moved['viaCompanyId']) == ('small', 'acme')
    moved = client.patch('/api/events/' + e['id'], json={'companyId': 'other-agency'}).json()  # to an agency: dropped
    assert (moved['companyId'], moved['viaCompanyId']) == ('other-agency', None)
    e = make_event(companyId='big', viaCompanyId='acme')
    moved = client.patch('/api/events/' + e['id'], json={'companyId': None}).json()  # to no company: dropped
    assert (moved['companyId'], moved['viaCompanyId']) == (None, None)
    # One the patch sends is checked as it is: an agency's event has none, and neither has an event with no company.
    assert client.patch('/api/events/' + e['id'], json={'companyId': 'other-agency', 'viaCompanyId': 'acme'}).status_code == 422
    assert client.patch('/api/events/' + e['id'], json={'companyId': None, 'viaCompanyId': 'acme'}).status_code == 422


def test_passive_message_requires_a_company(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Direct Co')
    r = client.post('/api/events', json={'date': '2026-10-08', 'event': 'passive_message'})
    assert r.status_code == 422 and 'needs a company' in str(r.json()['detail'])
    assert make_event(event='passive_message', companyId='direct-co')['event'] == 'passive_message'
    assert make_event(event='passive_message', companyId='acme')['event'] == 'passive_message'


def test_the_company_requirement_also_holds_when_editing(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Direct Co')
    passive = make_event(event='passive_message', companyId='acme')
    assert client.patch('/api/events/' + passive['id'], json={'companyId': None}).status_code == 422
    assert client.patch('/api/events/' + passive['id'], json={'companyId': 'direct-co'}).status_code == 200
    note = make_event(event='note')
    assert client.patch('/api/events/' + note['id'], json={'event': 'passive_message'}).status_code == 422  # no company on it
    assert client.put('/api/events/' + passive['id'], json={'date': '2026-10-08', 'event': 'passive_message'}).status_code == 422
    assert client.patch('/api/events/' + note['id'], json={'event': 'passive_message', 'companyId': 'acme'}).status_code == 200


def test_the_status_of_a_company_is_derived_from_its_latest_event(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Big')
    status = lambda name: client.get('/api/companies/' + name).json()['status']  # noqa: E731
    assert status('acme') == 'active'                               # no events yet
    make_event(date='2026-10-01', event='note', companyId='acme')
    rejection = make_event(date='2026-10-02', event='rejection', companyId='acme')
    assert status('acme') == 'archived'                            # the latest event closes the process
    make_event(date='2026-10-03', event='note', companyId='acme')
    assert status('acme') == 'active'                              # a later one reactivates it
    make_event(date='2026-10-03', time='08:00', event='archive', companyId='acme')
    assert status('acme') == 'archived'                            # a closing event wins a tie on the day, whatever its time
    make_event(date='2026-10-01', event='note', companyId='acme')   # an older event changes nothing
    assert status('acme') == 'archived'
    client.delete('/api/events/' + rejection['id'])
    assert status('acme') == 'archived'
    make_event(event='pending', jdUrl='https://x')                 # an unlinked event touches nobody
    assert status('big') == 'active'
    assert [c['status'] for c in client.get('/api/companies').json()] == ['archived', 'active']  # the list says the same


def test_closed_by_says_how_an_archived_company_was_closed(client, make_agency, make_event):
    for name in ('Mute', 'Answered', 'Rejected', 'Flagged', 'Waiting', 'Offered', 'Reopened', 'Fresh'):
        make_agency(name)
    closed_by = lambda name: client.get('/api/companies/' + name).json()['closedBy']  # noqa: E731
    make_event(date='2026-10-01', event='application', companyId='mute')
    assert closed_by('mute') is None                               # still active: nobody has closed it
    make_event(date='2026-10-20', event='archive', companyId='mute')
    assert closed_by('mute') == 'ghosted'                          # archived by hand
    assert client.get('/api/companies/mute').json()['status'] == 'archived'
    make_event(date='2026-10-01', event='application', companyId='answered')
    make_event(date='2026-10-05', event='hr_intro', companyId='answered')
    make_event(date='2026-10-20', event='archive', companyId='answered')
    assert closed_by('answered') == 'ghosted'                      # an archive by hand is ghosted, whatever came before it
    for name, event in (('rejected', 'rejection'), ('flagged', 'red_flag'), ('waiting', 'on_hold'), ('offered', 'offer')):
        make_event(date='2026-10-01', event='application', companyId=name)
        make_event(date='2026-10-05', event=event, companyId=name)
        assert closed_by(name) == event                            # the type of the event that closed it
    make_event(date='2026-10-01', event='application', companyId='reopened')
    make_event(date='2026-10-02', event='archive', companyId='reopened')
    make_event(date='2026-10-03', event='application', companyId='reopened')
    assert closed_by('reopened') is None                           # applied again: active
    assert closed_by('fresh') is None                              # no events
    assert [c['closedBy'] for c in client.get('/api/companies').json()] == [  # the list says the same, by name
        'ghosted', 'red_flag', None, 'ghosted', 'offer', 'rejection', None, 'on_hold'
    ]


def test_an_agency_is_archived_with_the_latest_event_of_its_clients(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Big')
    make_event(date='2026-10-01', event='note', companyId='big', viaCompanyId='acme')
    make_event(date='2026-10-02', event='rejection', companyId='big', viaCompanyId='acme')
    assert client.get('/api/companies/acme').json()['status'] == 'archived'
    assert client.get('/api/companies/big').json()['status'] == 'archived'

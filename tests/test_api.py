"""The JSON API: companies (agencies and clients) and events, through the real app (in-process)."""


# ---------- companies ----------


def test_create_gives_a_slug_id_and_the_full_shape(make_agency):
    a = make_agency('Café & Co', website='https://cafe.example', recruiters=['https://linkedin.com/in/ana', ' ', 'https://linkedin.com/in/bo'])
    assert a['id'] == 'cafe-co'
    assert a['status'] == 'active' and a['closedBy'] is None
    assert a['recruiters'] == ['https://linkedin.com/in/ana', 'https://linkedin.com/in/bo']  # blank dropped, order kept
    assert set(a) == {'id', 'name', 'companyType', 'notes', 'website', 'linkedin', 'applicationLink', 'recruiters', 'viaCompanyId', 'status', 'closedBy'}


def test_a_name_that_exists_is_refused_ignoring_case_whatever_the_type(client, make_agency):
    make_agency('Acme')
    for company_type in ('agency', 'client'):  # the same name as a client is the duplicate the front end used to make
        r = client.post('/api/companies', json={'name': ' ACME ', 'companyType': company_type})
        assert r.status_code == 409
        assert 'already exists' in r.json()['detail']


def test_ids_never_collide(make_agency, make_client):
    make_agency('A.B')
    assert make_client('A B')['id'] == 'a-b-2'


def test_validation(client, make_client):
    assert client.post('/api/companies', json={}).status_code == 422
    assert client.post('/api/companies', json={'name': 'X'}).status_code == 422  # the type is always said
    assert client.post('/api/companies', json={'name': '!!!', 'companyType': 'agency'}).status_code == 422
    assert client.post('/api/companies', json={'name': 'X', 'companyType': 'employer'}).status_code == 422
    assert client.post('/api/companies', json={'name': 'X', 'companyType': 'agency', 'recruiters': 'nope'}).status_code == 422
    assert client.post('/api/companies', json={'name': 'C', 'companyType': 'client', 'viaCompanyId': 'ghost'}).status_code == 422
    make_client('Solo')
    assert client.post('/api/companies', json={'name': 'D', 'companyType': 'client', 'viaCompanyId': 'solo'}).status_code == 422  # a client is not an agency
    assert client.post('/api/companies', json={'name': 'E', 'companyType': 'agency', 'viaCompanyId': 'solo'}).status_code == 422  # only a client has a via


def test_old_firestore_data_is_accepted(client):
    r = client.post('/api/companies', json={'name': 'Old', 'companyType': 'agency', 'recruiters': None, 'notes': None})
    assert (r.status_code, r.json()['status'], r.json()['recruiters'], r.json()['notes']) == (201, 'active', [], '')


def test_patch_touches_only_what_was_sent(client, make_agency):
    make_agency('Acme', notes='staffing', recruiters=['https://x'])
    body = client.patch('/api/companies/acme', json={'website': 'https://acme.example'}).json()
    assert (body['notes'], body['recruiters'], body['website']) == ('staffing', ['https://x'], 'https://acme.example')
    assert client.patch('/api/companies/acme', json={'recruiters': []}).json()['recruiters'] == []
    assert client.patch('/api/companies/acme', json={'website': ''}).json()['website'] is None  # blank clears it
    assert client.patch('/api/companies/acme', json={'name': None}).status_code == 422
    assert client.patch('/api/companies/acme', json={'companyType': None}).status_code == 422


def test_replacing_the_recruiters_in_place_keeps_their_order(client, make_agency):
    make_agency('Acme', recruiters=['https://a', 'https://b'])
    assert client.patch('/api/companies/acme', json={'recruiters': ['https://b', 'https://a', 'https://c']}).json()['recruiters'] == ['https://b', 'https://a', 'https://c']


def test_renaming_keeps_the_id_and_cannot_take_a_name(client, make_agency, make_client):
    make_agency('Acme')
    make_client('Zeta')
    body = client.patch('/api/companies/acme', json={'name': 'Acme Inc'}).json()
    assert (body['id'], body['name']) == ('acme', 'Acme Inc')
    assert client.patch('/api/companies/acme', json={'name': 'zeta'}).status_code == 409  # a client's name, too
    assert client.patch('/api/companies/acme', json={'name': 'ACME INC'}).status_code == 200  # its own name, other case


def test_put_replaces_and_creates(client, make_agency):
    make_agency('Acme', notes='staffing', website='https://x')
    body = client.put('/api/companies/acme', json={'name': 'Acme', 'companyType': 'agency', 'notes': 'recruiting'}).json()
    assert (body['notes'], body['website']) == ('recruiting', None)  # the website wasn't sent, so it's gone
    r = client.put('/api/companies/brand-new', json={'name': 'Brand New', 'companyType': 'client'})
    assert (r.status_code, r.json()['id']) == (200, 'brand-new')
    assert client.put('/api/companies/has%2Fslash', json={'name': 'Slash', 'companyType': 'agency'}).status_code in (400, 404, 405)  # no such route: refused either way


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


def test_the_list_filters_by_type(client, make_agency, make_client):
    make_agency('Acme')
    make_client('Big')
    assert [c['name'] for c in client.get('/api/companies', params={'companyType': 'client'}).json()] == ['Big']
    assert [c['name'] for c in client.get('/api/companies', params={'companyType': 'agency'}).json()] == ['Acme']
    assert len(client.get('/api/companies').json()) == 2
    assert client.get('/api/companies', params={'companyType': 'both'}).status_code == 422


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


def test_unknown_ids_are_404(client):
    assert client.get('/api/companies/ghost').status_code == 404
    assert client.patch('/api/companies/ghost', json={}).status_code == 404
    assert client.delete('/api/events/ghost').status_code == 404


def test_the_old_agency_and_client_routes_are_gone(client):
    assert client.get('/api/agencies').status_code == 404
    assert client.get('/api/clients').status_code == 404


def test_lists_are_sorted_by_name_ignoring_case(client, make_agency):
    for name in ('zeta', 'Alpha', 'beta'):
        make_agency(name)
    assert [a['name'] for a in client.get('/api/companies').json()] == ['Alpha', 'beta', 'zeta']


# ---------- events ----------


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


def test_the_old_front_end_fields_are_accepted_and_ignored(make_agency, make_event):
    make_agency('Acme')
    e = make_event(companyId='acme', companyLabel='whatever', id='forced')
    assert e['id'] != 'forced' and e['companyLabel'] == 'Acme'


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


def test_blank_time_and_links_become_null(make_event):
    e = make_event(time='', jdUrl='  ', applyType='')
    assert (e['time'], e['jdUrl'], e['applyType']) == (None, None, None)


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


def test_patch_put_delete(client, make_agency, make_event):
    make_agency('Acme')
    e = make_event(companyId='acme', notes='first', time='10:00')
    body = client.patch('/api/events/' + e['id'], json={'notes': 'second'}).json()
    assert (body['notes'], body['time']) == ('second', '10:00')
    body = client.put('/api/events/' + e['id'], json={'date': '2026-10-09', 'event': 'hr_intro', 'companyId': 'acme'}).json()
    assert (body['date'], body['time'], body['notes']) == ('2026-10-09', None, '')  # PUT replaces everything
    assert client.delete('/api/events/' + e['id']).status_code == 204
    assert client.get('/api/events').json() == []


def test_list_is_newest_first_and_filterable(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Big')
    make_event(date='2026-10-01', jdUrl='https://a')
    make_event(date='2026-10-03', time='09:00', event='hr_intro', companyId='acme')
    make_event(date='2026-10-03', time='15:00', event='hr_intro', companyId='big', viaCompanyId='acme')
    events = client.get('/api/events').json()
    assert [(e['date'], e['time']) for e in events] == [('2026-10-03', '15:00'), ('2026-10-03', '09:00'), ('2026-10-01', None)]
    assert len(client.get('/api/events', params={'companyId': 'acme'}).json()) == 2  # its own, and its client's
    assert len(client.get('/api/events', params={'companyId': 'big'}).json()) == 1
    assert len(client.get('/api/events', params={'event': 'hr_intro', 'companyId': 'acme'}).json()) == 2
    assert len(client.get('/api/events', params={'jdUrl': 'https://a'}).json()) == 1
    assert client.get('/api/events', params={'event': 'party'}).status_code == 422


def test_docs_are_served_and_list_the_new_event_type(client):
    assert client.get('/docs').status_code == 200
    schema = client.get('/openapi.json').json()
    assert 'passive_message' in schema['components']['schemas']['EventType']['enum']
    assert {'/api/events', '/api/companies/{company_id}', '/api/companies', '/api/export', '/api/stream'} <= set(schema['paths'])
    assert not {'/api/agencies', '/api/clients'} & set(schema['paths'])

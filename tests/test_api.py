"""The JSON API: agencies, clients and events, through the real app (in-process)."""


# ---------- agencies and clients ----------


def test_create_gives_a_slug_id_and_the_full_shape(make_agency):
    a = make_agency('Café & Co', website='https://cafe.example', recruiters=['https://linkedin.com/in/ana', ' ', 'https://linkedin.com/in/bo'])
    assert a['id'] == 'cafe-co'
    assert a['status'] == 'active'
    assert a['recruiters'] == ['https://linkedin.com/in/ana', 'https://linkedin.com/in/bo']  # blank dropped, order kept
    assert set(a) == {'id', 'name', 'type', 'website', 'linkedin', 'applicationLink', 'recruiters', 'status'}


def test_a_name_that_exists_is_refused_ignoring_case(client, make_agency):
    make_agency('Acme')
    r = client.post('/api/agencies', json={'name': ' ACME '})
    assert r.status_code == 409
    assert 'already exists' in r.json()['detail']


def test_ids_never_collide(make_agency):
    make_agency('A.B')
    assert make_agency('A B')['id'] == 'a-b-2'


def test_validation(client):
    assert client.post('/api/agencies', json={}).status_code == 422
    assert client.post('/api/agencies', json={'name': '!!!'}).status_code == 422
    assert client.post('/api/agencies', json={'name': 'X', 'recruiters': 'nope'}).status_code == 422
    assert client.post('/api/agencies', json={'name': 'X', 'status': 'sleepy'}).status_code == 422
    assert client.post('/api/clients', json={'name': 'C', 'viaAgencyId': 'ghost'}).status_code == 422


def test_old_firestore_data_is_accepted(client):
    r = client.post('/api/agencies', json={'name': 'Old', 'status': None, 'recruiters': None, 'type': None})
    assert (r.status_code, r.json()['status'], r.json()['recruiters'], r.json()['type']) == (201, 'active', [], '')


def test_patch_touches_only_what_was_sent(client, make_agency):
    make_agency('Acme', type='staffing', recruiters=['https://x'])
    body = client.patch('/api/agencies/acme', json={'website': 'https://acme.example'}).json()
    assert (body['type'], body['recruiters'], body['website']) == ('staffing', ['https://x'], 'https://acme.example')
    assert client.patch('/api/agencies/acme', json={'recruiters': []}).json()['recruiters'] == []
    assert client.patch('/api/agencies/acme', json={'website': ''}).json()['website'] is None  # blank clears it
    assert client.patch('/api/agencies/acme', json={'name': None}).status_code == 422


def test_replacing_the_recruiters_in_place_keeps_their_order(client, make_agency):
    make_agency('Acme', recruiters=['https://a', 'https://b'])
    assert client.patch('/api/agencies/acme', json={'recruiters': ['https://b', 'https://a', 'https://c']}).json()['recruiters'] == ['https://b', 'https://a', 'https://c']


def test_renaming_keeps_the_id_and_cannot_take_a_name(client, make_agency):
    make_agency('Acme')
    make_agency('Zeta')
    body = client.patch('/api/agencies/acme', json={'name': 'Acme Inc'}).json()
    assert (body['id'], body['name']) == ('acme', 'Acme Inc')
    assert client.patch('/api/agencies/acme', json={'name': 'zeta'}).status_code == 409
    assert client.patch('/api/agencies/acme', json={'name': 'ACME INC'}).status_code == 200  # its own name, other case


def test_put_replaces_and_creates(client, make_agency):
    make_agency('Acme', type='staffing', website='https://x')
    body = client.put('/api/agencies/acme', json={'name': 'Acme', 'type': 'recruiting'}).json()
    assert (body['type'], body['website']) == ('recruiting', None)  # the website wasn't sent, so it's gone
    r = client.put('/api/agencies/brand-new', json={'name': 'Brand New'})
    assert (r.status_code, r.json()['id']) == (200, 'brand-new')
    assert client.put('/api/agencies/has%2Fslash', json={'name': 'Slash'}).status_code in (400, 404, 405)  # no such route: refused either way


def test_clients_via_agency_and_direct(client, make_agency, make_client):
    make_agency('Acme')
    via, direct = make_client('Big', viaAgencyId='acme'), make_client('Direct Co')
    assert (via['viaAgencyId'], direct['viaAgencyId']) == ('acme', None)
    assert client.patch('/api/clients/big', json={'viaAgencyId': None}).json()['viaAgencyId'] is None
    assert client.patch('/api/clients/big', json={'viaAgencyId': 'ghost'}).status_code == 422


def test_deleting_a_company_that_still_has_events_is_refused_with_the_count(client, make_agency, make_event):
    make_agency('Acme')
    make_event(agencyId='acme')
    make_event(agencyId='acme')
    r = client.delete('/api/agencies/acme')
    assert r.status_code == 409 and '2 events' in r.json()['detail']
    assert client.get('/api/agencies/acme').status_code == 200


def test_deleting_an_agency_without_events_makes_its_clients_direct(client, make_agency, make_client):
    make_agency('Acme')
    make_client('Big', viaAgencyId='acme')
    assert client.delete('/api/agencies/acme').status_code == 204
    assert client.get('/api/clients/big').json()['viaAgencyId'] is None


def test_unknown_ids_are_404(client):
    assert client.get('/api/agencies/ghost').status_code == 404
    assert client.patch('/api/clients/ghost', json={}).status_code == 404
    assert client.delete('/api/events/ghost').status_code == 404


def test_lists_are_sorted_by_name_ignoring_case(client, make_agency):
    for name in ('zeta', 'Alpha', 'beta'):
        make_agency(name)
    assert [a['name'] for a in client.get('/api/agencies').json()] == ['Alpha', 'beta', 'zeta']


# ---------- events ----------


def test_company_label_is_derived_from_the_links(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Big', viaAgencyId='acme')
    make_client('Direct Co')
    assert make_event(agencyId='acme')['companyLabel'] == 'Acme'
    assert make_event(agencyId='acme', clientId='big')['companyLabel'] == 'Acme'  # the agency's own name, as before
    assert make_event(clientId='direct-co')['companyLabel'] == 'Direct Co'
    assert make_event(event='pending', jdUrl='https://x')['companyLabel'] == '—'
    client.patch('/api/agencies/acme', json={'name': 'Acme Inc'})
    assert client.get('/api/events', params={'agencyId': 'acme'}).json()[0]['companyLabel'] == 'Acme Inc'  # follows a rename


def test_the_old_front_end_fields_are_accepted_and_ignored(make_agency, make_event):
    make_agency('Acme')
    e = make_event(agencyId='acme', companyLabel='whatever', id='forced')
    assert e['id'] != 'forced' and e['companyLabel'] == 'Acme'


def test_event_validation(client, make_agency):
    make_agency('Acme')
    bad = [
        {'date': '2026-13-45', 'event': 'note'},
        {'date': '2026-10-08', 'event': 'party'},
        {'date': '2026-10-08', 'event': 'note', 'time': '25:00'},
        {'date': '2026-10-08', 'event': 'note', 'agencyId': 'ghost'},
        {'date': '2026-10-08', 'event': 'note', 'clientId': 'ghost'},
        {'date': '2026-10-08', 'event': 'application', 'applyType': 'pigeon'},
        {'event': 'note'},
    ]
    for body in bad:
        assert client.post('/api/events', json=body).status_code == 422, body


def test_blank_time_and_links_become_null(make_event):
    e = make_event(time='', jdUrl='  ', applyType='')
    assert (e['time'], e['jdUrl'], e['applyType']) == (None, None, None)


def test_passive_message_requires_an_agency_or_a_client(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Direct Co')
    r = client.post('/api/events', json={'date': '2026-10-08', 'event': 'passive_message'})
    assert r.status_code == 422 and 'needs an agency or a client' in str(r.json()['detail'])
    assert make_event(event='passive_message', clientId='direct-co')['event'] == 'passive_message'
    assert make_event(event='passive_message', agencyId='acme')['event'] == 'passive_message'


def test_the_company_requirement_also_holds_when_editing(client, make_agency, make_client, make_event):
    make_agency('Acme')
    make_client('Direct Co')
    passive = make_event(event='passive_message', agencyId='acme')
    assert client.patch('/api/events/' + passive['id'], json={'agencyId': None}).status_code == 422
    assert client.patch('/api/events/' + passive['id'], json={'agencyId': None, 'clientId': 'direct-co'}).status_code == 200
    note = make_event(event='note')
    assert client.patch('/api/events/' + note['id'], json={'event': 'passive_message'}).status_code == 422  # no company on it
    assert client.put('/api/events/' + passive['id'], json={'date': '2026-10-08', 'event': 'passive_message'}).status_code == 422
    assert client.patch('/api/events/' + note['id'], json={'event': 'passive_message', 'agencyId': 'acme'}).status_code == 200


def test_a_new_event_sets_the_agency_status_and_editing_does_not(client, make_agency, make_event):
    make_agency('Acme')
    status = lambda: client.get('/api/agencies/acme').json()['status']  # noqa: E731
    assert status() == 'active'
    rejection = make_event(event='rejection', agencyId='acme')
    assert status() == 'archived'                  # a closing event archives it
    make_event(event='note', agencyId='acme')
    assert status() == 'active'                    # any other new event reactivates it
    make_event(event='archive', agencyId='acme')
    assert status() == 'archived'
    client.patch('/api/events/' + rejection['id'], json={'notes': 'edited'})
    assert status() == 'archived'                  # editing never flips it
    make_event(event='pending', jdUrl='https://x')  # an unlinked event touches nobody
    assert status() == 'archived'


def test_patch_put_delete(client, make_agency, make_event):
    make_agency('Acme')
    e = make_event(agencyId='acme', notes='first', time='10:00')
    body = client.patch('/api/events/' + e['id'], json={'notes': 'second'}).json()
    assert (body['notes'], body['time']) == ('second', '10:00')
    body = client.put('/api/events/' + e['id'], json={'date': '2026-10-09', 'event': 'hr_intro', 'agencyId': 'acme'}).json()
    assert (body['date'], body['time'], body['notes']) == ('2026-10-09', None, '')  # PUT replaces everything
    assert client.delete('/api/events/' + e['id']).status_code == 204
    assert client.get('/api/events').json() == []


def test_list_is_newest_first_and_filterable(client, make_agency, make_event):
    make_agency('Acme')
    make_event(date='2026-10-01', jdUrl='https://a')
    make_event(date='2026-10-03', time='09:00', event='hr_intro', agencyId='acme')
    make_event(date='2026-10-03', time='15:00', event='hr_intro', agencyId='acme')
    events = client.get('/api/events').json()
    assert [(e['date'], e['time']) for e in events] == [('2026-10-03', '15:00'), ('2026-10-03', '09:00'), ('2026-10-01', None)]
    assert len(client.get('/api/events', params={'agencyId': 'acme'}).json()) == 2
    assert len(client.get('/api/events', params={'event': 'hr_intro', 'agencyId': 'acme'}).json()) == 2
    assert len(client.get('/api/events', params={'jdUrl': 'https://a'}).json()) == 1
    assert client.get('/api/events', params={'event': 'party'}).status_code == 422


def test_docs_are_served_and_list_the_new_event_type(client):
    assert client.get('/docs').status_code == 200
    schema = client.get('/openapi.json').json()
    assert 'passive_message' in schema['components']['schemas']['EventType']['enum']
    assert {'/api/events', '/api/agencies/{agency_id}', '/api/clients', '/api/export', '/api/stream'} <= set(schema['paths'])

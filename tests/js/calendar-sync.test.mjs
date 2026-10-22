// The Google Calendar button and its popup (public/js/calendar-sync.js). Run with: node --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

const { EVENT_LABELS } = await import('../../public/js/events.js')
const { applySyncState, confirmLabel, firstWithoutCompany, repeatingNote, syncPayload, syncRowsHtml, syncSummary, weekDates } =
  await import('../../public/js/calendar-sync.js')

function fakeButton() {
  const attributes = {}
  return { disabled: false, title: '', setAttribute: (k, v) => (attributes[k] = v), attributes }
}

const hr = { key: 'a', summary: 'HR intro with Acme', notes: 'HR intro with Acme\n\nCompany: Acme', date: '2026-10-13', time: '15:00', company: 'Acme', companyType: 'agency', via: null, action: 'new', type: 'hr_intro' }
const tech = { ...hr, key: 'b', summary: 'Tech interview', company: null, companyType: null, type: 'tech_interview' }
const moved = { ...hr, key: 'c', action: 'moved' }

test('the button is off, with its own hint, until a calendar is set', () => {
  const button = fakeButton()
  applySyncState(button, false)
  assert.equal(button.disabled, true)
  assert.equal(button.title, 'Google Calendar not synced')
  assert.equal(button.attributes['aria-label'], 'Google Calendar not synced')
})

test('with a calendar set the button is on and says what it does', () => {
  const button = fakeButton()
  applySyncState(button, false)
  applySyncState(button, true)
  assert.equal(button.disabled, false)
  assert.equal(button.title, 'Sync Google Calendar')
  assert.equal(button.attributes['aria-label'], 'Sync Google Calendar')
})

test('the week to sync is Monday to Friday, as local dates', () => {
  assert.deepEqual(weekDates(new Date(2026, 9, 12)), { start: '2026-10-12', end: '2026-10-16' })
  assert.deepEqual(weekDates(new Date(2026, 11, 28)), { start: '2026-12-28', end: '2027-01-01' }) // across the new year
})

test('the popup lists each event ticked, with the type the server suggested', () => {
  const html = syncRowsHtml([hr, tech])
  assert.equal((html.match(/type="checkbox"/g) ?? []).length, 2)
  assert.equal((html.match(/ checked /g) ?? []).length, 2)
  const { emoji: hrEmoji } = EVENT_LABELS.hr_intro
  const { emoji: techEmoji } = EVENT_LABELS.tech_interview
  assert.ok(hrEmoji && techEmoji && hrEmoji !== techEmoji)
  assert.ok(html.includes(`<option value="hr_intro" selected>${hrEmoji} HR Intro</option><option value="tech_interview">${techEmoji} Technical interview</option>`))
  assert.ok(html.includes(`<option value="hr_intro">${hrEmoji} HR Intro</option><option value="tech_interview" selected>${techEmoji} Technical interview</option>`))
  assert.match(html, /2026-10-13 15:00/)
})

test('the popup offers the three interviews of the calendar: HR, technical and culture', () => {
  const html = syncRowsHtml([{ ...hr, type: 'culture_interview' }])
  const options = [...html.matchAll(/<option value="([a-z]+_[a-z_]+)"( selected)?>/g)].map((m) => m[1])
  assert.deepEqual([...options].sort(), ['culture_interview', 'hr_intro', 'tech_interview'])
  assert.match(html, /<option value="culture_interview" selected>/)
})

test('a new event has a company with its tag and, for a client, its agency, filled with what the server offered', () => {
  const html = syncRowsHtml([hr, { ...tech, company: 'Beta', companyType: 'client', via: 'Acme' }])
  for (const field of ['company', 'company-type', 'via']) assert.equal((html.match(new RegExp(`data-${field}="`, 'g')) ?? []).length, 2)
  assert.match(html, /data-company="0"[^>]*value="Acme"/)
  assert.match(html, /data-company="1"[^>]*value="Beta"/)  // a client is the company, and its agency goes in Via agency
  assert.match(html, /data-via="0"[^>]*value=""/)
  assert.match(html, /data-via="1"[^>]*value="Acme"/)
  assert.match(html, /data-company-type="0"[^>]*><option value="agency" selected>Agency<\/option><option value="client">Client<\/option>/)
  assert.match(html, /data-company-type="1"[^>]*><option value="agency">Agency<\/option><option value="client" selected>Client<\/option>/)
  assert.match(html, /data-via-wrap="0" class="pl-7 hidden"/)  // Via agency is only for a client
  assert.match(html, /data-via-wrap="1" class="pl-7"/)
  assert.match(html, /list="company-list"/)
  assert.match(html, /list="agency-list"/)
  assert.doesNotMatch(html, /client-list/)
})

test('a moved event shows its company without fields, and keeps its type fixed', () => {
  const html = syncRowsHtml([{ ...moved, company: 'Beta', companyType: 'client', via: 'Acme' }])
  assert.match(html, /moved in Google/)
  assert.match(html, /Company: Acme → Beta \(stays as it is\)/)
  assert.doesNotMatch(html, /data-company|data-company-type|data-via/)
  assert.equal((html.match(/<select[^>]* disabled/g) ?? []).length, 1)
})

test('the notes the event would get show on hover', () => {
  assert.match(syncRowsHtml([hr]), /title="HR intro with Acme\n\nCompany: Acme"/)
})

test('what comes from Google is escaped', () => {
  const html = syncRowsHtml([{ ...hr, summary: '<img src=x onerror=alert(1)>', company: '"><script>', via: '"><script>', notes: '<b>x</b>' }])
  assert.doesNotMatch(html, /<img|<script>|<b>x/)
})

test('only the ticked rows are sent, each with its type and, when new, its company', () => {
  const items = [hr, tech, moved]
  const state = [
    { checked: true, type: 'tech_interview', company: ' Acme ', companyType: 'agency', via: 'ignored' },
    { checked: false, type: 'hr_intro', company: '', companyType: 'agency', via: '' },
    { checked: true, type: 'hr_intro', company: '', companyType: 'agency', via: '' },
  ]
  assert.deepEqual(syncPayload(items, state), [
    { key: 'a', type: 'tech_interview', company: 'Acme', companyType: 'agency', via: null },  // an agency has no via
    { key: 'c', type: 'hr_intro' },
  ])
  const client = [{ checked: true, type: 'hr_intro', company: 'Beta', companyType: 'client', via: ' Acme ' }, state[1], state[2]]
  assert.deepEqual(syncPayload(items, client)[0], { key: 'a', type: 'hr_intro', company: 'Beta', companyType: 'client', via: 'Acme' })
  assert.deepEqual(syncPayload(items, state.map((s) => ({ ...s, checked: false }))), [])
})

test('a ticked new event with no company is found, an unticked one or a moved one is not', () => {
  const items = [hr, tech, moved]
  const state = [
    { checked: true, type: 'hr_intro', company: 'Acme', companyType: 'agency', via: '' },
    { checked: true, type: 'hr_intro', company: '  ', companyType: 'agency', via: '' },
    { checked: true, type: 'hr_intro', company: '', companyType: 'agency', via: '' },
  ]
  assert.equal(firstWithoutCompany(items, state), tech)
  assert.equal(firstWithoutCompany(items, [state[0], { ...state[1], company: 'Beta' }, state[2]]), null)
  assert.equal(firstWithoutCompany(items, [state[0], { ...state[1], checked: false }, state[2]]), null)
})

test('the confirm button counts what is ticked', () => {
  assert.equal(confirmLabel(0), 'Nothing selected')
  assert.equal(confirmLabel(1), 'Add 1 event')
  assert.equal(confirmLabel(3), 'Add 3 events')
})

test('the messages say what changed and what was left out', () => {
  assert.equal(syncSummary({ created: 0, updated: 0 }), 'Nothing changed.')
  assert.equal(syncSummary({ created: 1, updated: 0 }), '1 event added.')
  assert.equal(syncSummary({ created: 2, updated: 1 }), '2 events added, 1 event moved.')
  assert.equal(repeatingNote(0), '')
  assert.equal(repeatingNote(1), ' 1 repeating event not imported.')
  assert.equal(repeatingNote(2), ' 2 repeating events not imported.')
})

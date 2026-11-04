// The Follow Up page (public/js/follow-up.js): the days count from the LAST application, not the first event.
// Run with: node --import ./tests/js/setup.mjs --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => [] })

const { computeStale, lastApplicationDate } = await import('../../public/js/follow-up.js')
const { toISODate } = await import('../../public/js/dates.js')

const daysAgo = (n) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return toISODate(d)
}
const ev = (id, event, ago, extra = {}) => ({ id, event, date: daysAgo(ago), ...extra })

test('the date is the latest application, not the first event', () => {
  const matches = [ev('a', 'note', 90), ev('b', 'application', 60), ev('c', 'application', 5)]
  assert.equal(lastApplicationDate(matches), daysAgo(5))
})

test('a passive message counts as an application', () => {
  const matches = [ev('a', 'application', 60), ev('b', 'passive_message', 3)]
  assert.equal(lastApplicationDate(matches), daysAgo(3))
})

test('an interview, a note or a rejection after the last application does not move the date', () => {
  const matches = [ev('a', 'application', 40), ev('b', 'hr_intro', 10), ev('c', 'note', 2)]
  assert.equal(lastApplicationDate(matches), daysAgo(40))
})

test('with no application at all it falls back to the last event of any kind, and with no events there is no date', () => {
  assert.equal(lastApplicationDate([ev('a', 'note', 20), ev('b', 'hr_intro', 7)]), daysAgo(7))
  assert.equal(lastApplicationDate([]), null)
})

const company = (id, name, extra = {}) => [id, { id, name, companyType: 'agency', status: 'active', viaCompanyId: null, ...extra }]

test('an agency that applied again recently is not stale: the days count from the newest application', () => {
  const deps = {
    companiesMap: new Map([company('acme', 'Acme Staffing')]),
    applications: [ev('a', 'application', 60, { companyId: 'acme' }), ev('b', 'application', 3, { companyId: 'acme' })],
  }
  assert.deepEqual(computeStale(30, deps), [])
  const found = computeStale(2, deps)
  assert.equal(found.length, 1)
  assert.equal(found[0].days, 3)
  assert.equal(found[0].company.id, 'acme')
})

test('the days of an old application show up at the threshold, whatever came before it', () => {
  const deps = {
    companiesMap: new Map([company('globex', 'Globex')]),
    applications: [ev('a', 'note', 100, { companyId: 'globex' }), ev('b', 'application', 35, { companyId: 'globex' })],
  }
  const found = computeStale(30, deps)
  assert.equal(found.length, 1)
  assert.equal(found[0].days, 35)
})

test('an archived company is left out, agency or client', () => {
  const deps = {
    companiesMap: new Map([company('old', 'Old Agency', { status: 'archived' }), company('hooli', 'Hooli', { companyType: 'client', status: 'archived' })]),
    applications: [
      ev('a', 'application', 50, { companyId: 'old' }),
      ev('b', 'application', 50, { companyId: 'hooli' }),
      ev('c', 'rejection', 40, { companyId: 'hooli' }),
    ],
  }
  assert.deepEqual(computeStale(0, deps), [])
})

test('a client counts its own applications, and keeps its agency for the card', () => {
  const deps = {
    companiesMap: new Map([company('acme', 'Acme Staffing'), company('initech', 'Initech', { companyType: 'client', viaCompanyId: 'acme' })]),
    applications: [ev('a', 'application', 45, { companyId: 'initech', viaCompanyId: 'acme' }), ev('b', 'passive_message', 12, { companyId: 'initech', viaCompanyId: 'acme' })],
  }
  const found = computeStale(10, deps).find((r) => r.company.id === 'initech')
  assert.equal(found.days, 12)
  assert.equal(found.via.name, 'Acme Staffing')
})

test('an agency also counts the applications of its clients that came through it', () => {
  const deps = {
    companiesMap: new Map([company('acme', 'Acme Staffing'), company('initech', 'Initech', { companyType: 'client', viaCompanyId: 'acme' })]),
    applications: [ev('a', 'application', 20, { companyId: 'initech', viaCompanyId: 'acme' })],
  }
  const found = computeStale(10, deps)
  assert.deepEqual(found.map((r) => [r.company.id, r.days]).sort(), [['acme', 20], ['initech', 20]])
})

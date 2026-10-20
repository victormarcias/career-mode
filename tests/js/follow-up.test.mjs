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

test('an agency that applied again recently is not stale: the days count from the newest application', () => {
  const acme = { id: 'acme', name: 'Acme Staffing', status: 'active' }
  const deps = {
    agenciesMap: new Map([['acme', acme]]),
    clientsMap: new Map(),
    applications: [ev('a', 'application', 60, { agencyId: 'acme' }), ev('b', 'application', 3, { agencyId: 'acme' })],
  }
  assert.deepEqual(computeStale(30, deps), [])
  const found = computeStale(2, deps)
  assert.equal(found.length, 1)
  assert.equal(found[0].days, 3)
  assert.equal(found[0].entity.id, 'acme')
})

test('the days of an old application show up at the threshold, whatever came before it', () => {
  const globex = { id: 'globex', name: 'Globex', status: 'active' }
  const deps = {
    agenciesMap: new Map([['globex', globex]]),
    clientsMap: new Map(),
    applications: [ev('a', 'note', 100, { agencyId: 'globex' }), ev('b', 'application', 35, { agencyId: 'globex' })],
  }
  const found = computeStale(30, deps)
  assert.equal(found.length, 1)
  assert.equal(found[0].days, 35)
})

test('an archived agency and a client whose last event closed the process are left out', () => {
  const closed = { id: 'old', name: 'Old Agency', status: 'archived' }
  const hooli = { id: 'hooli', name: 'Hooli', viaAgencyId: null }
  const deps = {
    agenciesMap: new Map([['old', closed]]),
    clientsMap: new Map([['hooli', hooli]]),
    applications: [
      ev('a', 'application', 50, { agencyId: 'old' }),
      ev('b', 'application', 50, { clientId: 'hooli' }),
      ev('c', 'rejection', 40, { clientId: 'hooli' }),
    ],
  }
  assert.deepEqual(computeStale(0, deps), [])
})

test('a client counts its own applications, and keeps its agency for the card', () => {
  const via = { id: 'acme', name: 'Acme Staffing', status: 'active' }
  const initech = { id: 'initech', name: 'Initech', viaAgencyId: 'acme' }
  const deps = {
    agenciesMap: new Map([['acme', via]]),
    clientsMap: new Map([['initech', initech]]),
    applications: [ev('a', 'application', 45, { clientId: 'initech' }), ev('b', 'passive_message', 12, { clientId: 'initech' })],
  }
  const found = computeStale(10, deps)
  assert.equal(found.length, 1)
  assert.equal(found[0].kind, 'client')
  assert.equal(found[0].days, 12)
  assert.equal(found[0].via.name, 'Acme Staffing')
})

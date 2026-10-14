// What the company fields do with the names: the hint for a new one (companyHint, public/js/dom-utils.js) and
// the suggestions, which are only the active companies (activeCompanyNames, public/js/companies.js).
// Run with: node --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

const { companyHint, setNotice } = await import('../../public/js/dom-utils.js')
const { activeCompanyNames } = await import('../../public/js/companies.js')

test('the hint says which companies would be created, and nothing when they all exist', () => {
  const agencies = [{ id: 'acme', name: 'Acme' }]
  const clients = [{ id: 'beta', name: 'Beta' }]
  assert.equal(companyHint(agencies, clients, 'acme', 'BETA'), '') // found ignoring case
  assert.equal(companyHint(agencies, clients, 'Newco', ''), 'Will create the new agency "Newco".')
  assert.equal(companyHint(agencies, clients, '', 'Gamma'), 'Will create the new client "Gamma".')
  assert.equal(companyHint(agencies, clients, 'Newco', 'Gamma'), 'Will create the new agency "Newco" and the new client "Gamma".')
  assert.equal(companyHint(agencies, clients, '', ''), '')
})

test('a name matches by its id too, not only by its name', () => {
  assert.equal(companyHint([{ id: 'cwssg', name: 'CW Strategic Solutions Group' }], [], 'CW Strategic Solutions Group', ''), '')
  assert.equal(companyHint([{ id: 'acme-inc', name: 'ACME, Inc.' }], [], 'Acme Inc', ''), '')
})

test('the company fields suggest only the active agencies and clients', () => {
  const agencies = [
    { id: 'acme', name: 'Acme', status: 'active' },
    { id: 'old', name: 'Old Agency', status: 'archived' },
  ]
  const clients = [
    { id: 'open', name: 'Open Co' }, // its latest event does not close it
    { id: 'closed', name: 'Closed Co' }, // its latest event is a rejection
    { id: 'back', name: 'Back Co' }, // was rejected, then came back
    { id: 'fresh', name: 'Fresh Co' }, // no events yet
  ]
  const events = [
    { id: '1', clientId: 'open', event: 'hr_intro', date: '2026-10-01', time: '10:00' },
    { id: '2', clientId: 'closed', event: 'hr_intro', date: '2026-10-01', time: '10:00' },
    { id: '3', clientId: 'closed', event: 'rejection', date: '2026-10-05', time: '10:00' },
    { id: '4', clientId: 'back', event: 'rejection', date: '2026-10-02', time: '10:00' },
    { id: '5', clientId: 'back', event: 'hr_intro', date: '2026-10-08', time: '10:00' },
  ]
  assert.deepEqual(activeCompanyNames(agencies, clients, events), { agencies: ['Acme'], clients: ['Open Co', 'Back Co', 'Fresh Co'] })
  assert.deepEqual(activeCompanyNames([], [], []), { agencies: [], clients: [] })
})

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function fakeNotice() {
  const classes = new Set()
  return { textContent: '', classes, classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c) } }
}

test('a notice folds open with its text, and folds shut keeping the text until it is gone', async () => {
  const el = fakeNotice()
  setNotice(el, 'Will create the new agency "X".')
  assert.equal(el.textContent, 'Will create the new agency "X".')
  assert.ok(el.classes.has('is-open'))

  setNotice(el, '')
  assert.ok(!el.classes.has('is-open'))
  assert.equal(el.textContent, 'Will create the new agency "X".', 'the text stays while it folds')
  await sleep(300)
  assert.equal(el.textContent, '', 'and goes once it is folded')
})

test('a notice that opens again while folding keeps its new text', async () => {
  const el = fakeNotice()
  setNotice(el, 'one')
  setNotice(el, '')
  setNotice(el, 'two') // before the first one finished folding
  await sleep(300)
  assert.equal(el.textContent, 'two')
  assert.ok(el.classes.has('is-open'))
})

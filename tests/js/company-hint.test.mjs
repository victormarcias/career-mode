// What the company fields do with the names: the hint for a new one (companyHint, public/js/dom-utils.js) and
// the suggestions, which are only the active companies (activeCompanyNames, public/js/companies.js).
// Run with: node --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

const { companyFromNames, companyHint, companyNames, kindConflict, kindFor, setNotice } = await import('../../public/js/dom-utils.js')
const { activeCompanyNames } = await import('../../public/js/companies.js')

const agencies = [{ id: 'acme', name: 'Acme' }]
const clients = [{ id: 'beta', name: 'Beta' }]

test('the hint says which companies would be created, and nothing when they all exist', () => {
  assert.equal(companyHint(agencies, clients, 'ACME', 'agency'), '') // found ignoring case
  assert.equal(companyHint(agencies, clients, 'beta', 'client'), '')
  assert.equal(companyHint(agencies, clients, 'Newco', 'agency'), 'Will create the new agency "Newco".')
  assert.equal(companyHint(agencies, clients, 'Gamma', 'client'), 'Will create the new client "Gamma".')
  assert.equal(companyHint(agencies, clients, 'Gamma', 'client', 'Acme'), 'Will create the new client "Gamma".') // its agency exists
  assert.equal(companyHint(agencies, clients, 'Beta', 'client', 'Newco'), 'Will create the new agency "Newco".')
  assert.equal(companyHint(agencies, clients, 'Gamma', 'client', 'Newco'), 'Will create the new agency "Newco" and the new client "Gamma".')
  assert.equal(companyHint(agencies, clients, '', 'agency'), '')
})

test('a name that is already the other tag is said, not made twice', () => {
  assert.equal(companyHint(agencies, clients, 'Acme', 'client'), '"Acme" is already an agency.')
  assert.equal(companyHint(agencies, clients, 'Beta', 'agency'), '"Beta" is already a client.')
  assert.equal(kindConflict(agencies, clients, 'Acme', 'client'), 'agency')
  assert.equal(kindConflict(agencies, clients, 'Acme', 'agency'), null)
  assert.equal(kindConflict(agencies, clients, 'Newco', 'client'), null)
  // a name that is both, from before, is not a conflict for either tag, and the tag stays as it is
  const both = [{ id: 'galgo', name: 'Galgo' }]
  assert.equal(kindConflict(both, both, 'Galgo', 'client'), null)
  assert.equal(kindFor(both, both, 'Galgo', 'client'), 'client')
})

test('the tag follows the name of a company that exists, and stays for one that does not', () => {
  assert.equal(kindFor(agencies, clients, 'acme', 'client'), 'agency')
  assert.equal(kindFor(agencies, clients, 'BETA', 'agency'), 'client')
  assert.equal(kindFor(agencies, clients, 'Newco', 'client'), 'client')
  assert.equal(kindFor(agencies, clients, '', 'agency'), 'agency')
})

test('a company with its tag stands for an agency and a client name, and back', () => {
  assert.deepEqual(companyNames({ name: ' Acme ', kind: 'agency', via: 'ignored' }), { agency: 'Acme', client: '' })
  assert.deepEqual(companyNames({ name: 'Beta', kind: 'client', via: ' Acme ' }), { agency: 'Acme', client: 'Beta' })
  assert.deepEqual(companyNames({ name: 'Beta', kind: 'client', via: '' }), { agency: '', client: 'Beta' })
  assert.deepEqual(companyFromNames('Acme', ''), { name: 'Acme', kind: 'agency', via: '' })
  assert.deepEqual(companyFromNames('Acme', 'Beta'), { name: 'Beta', kind: 'client', via: 'Acme' })
  assert.deepEqual(companyFromNames('', 'Beta'), { name: 'Beta', kind: 'client', via: '' })
})

test('a name matches by its id too, not only by its name', () => {
  assert.equal(companyHint([{ id: 'cwssg', name: 'CW Strategic Solutions Group' }], [], 'CW Strategic Solutions Group', 'agency'), '')
  assert.equal(companyHint([{ id: 'acme-inc', name: 'ACME, Inc.' }], [], 'Acme Inc', 'agency'), '')
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

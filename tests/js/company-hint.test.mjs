// What the company fields do with the names: the hint for a new one (companyHint, public/js/dom-utils.js) and
// the suggestions, which are only the active companies (activeCompanyNames, public/js/companies.js).
// Run with: node --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

const { companyHint, findCompany, setNotice, typeConflict, typeFor } = await import('../../public/js/dom-utils.js')
const { activeCompanies } = await import('../../public/js/companies.js')

const companies = [
  { id: 'acme', name: 'Acme', companyType: 'agency' },
  { id: 'beta', name: 'Beta', companyType: 'client' },
]

test('the hint says which companies would be created, and nothing when they all exist', () => {
  assert.equal(companyHint(companies, 'ACME', 'agency'), '') // found ignoring case
  assert.equal(companyHint(companies, 'beta', 'client'), '')
  assert.equal(companyHint(companies, 'Newco', 'agency'), 'Will create the new agency "Newco".')
  assert.equal(companyHint(companies, 'Gamma', 'client'), 'Will create the new client "Gamma".')
  assert.equal(companyHint(companies, 'Gamma', 'client', 'Acme'), 'Will create the new client "Gamma".') // its agency exists
  assert.equal(companyHint(companies, 'Beta', 'client', 'Newco'), 'Will create the new agency "Newco".')
  assert.equal(companyHint(companies, 'Gamma', 'client', 'Newco'), 'Will create the new agency "Newco" and the new client "Gamma".')
  assert.equal(companyHint(companies, 'Newco', 'agency', 'ignored'), 'Will create the new agency "Newco".') // an agency has no via
  assert.equal(companyHint(companies, '', 'agency'), '')
})

test('a name that is already the other type is said, not made twice', () => {
  assert.equal(companyHint(companies, 'Acme', 'client'), '"Acme" is already an agency.')
  assert.equal(companyHint(companies, 'Beta', 'agency'), '"Beta" is already a client.')
  assert.equal(companyHint(companies, 'Gamma', 'client', 'Beta'), '"Beta" is already a client.') // the agency it came through has to be one
  assert.equal(typeConflict(companies, 'Acme', 'client'), 'agency')
  assert.equal(typeConflict(companies, 'Acme', 'agency'), null)
  assert.equal(typeConflict(companies, 'Newco', 'client'), null)
  assert.equal(typeConflict(companies, '', 'client'), null)
})

test('the type follows the name of a company that exists, and stays for one that does not', () => {
  assert.equal(typeFor(companies, 'acme', 'client'), 'agency')
  assert.equal(typeFor(companies, 'BETA', 'agency'), 'client')
  assert.equal(typeFor(companies, 'Newco', 'client'), 'client')
  assert.equal(typeFor(companies, '', 'agency'), 'agency')
})

test('a company is found by its name ignoring case, or by the id its slug gives, whatever its type', () => {
  assert.equal(findCompany(companies, ' beta ').id, 'beta')
  assert.equal(findCompany(companies, 'Newco'), null)
  assert.equal(findCompany([{ id: 'cwssg', name: 'CW Strategic Solutions Group', companyType: 'agency' }], 'CW Strategic Solutions Group').id, 'cwssg')
  assert.equal(findCompany([{ id: 'acme-inc', name: 'ACME, Inc.', companyType: 'agency' }], 'Acme Inc').id, 'acme-inc')
})

test('the company fields suggest only the active companies', () => {
  const list = [
    { id: 'acme', name: 'Acme', companyType: 'agency', status: 'active' },
    { id: 'old', name: 'Old Agency', companyType: 'agency', status: 'archived' },
    { id: 'open', name: 'Open Co', companyType: 'client', status: 'active' },
    { id: 'closed', name: 'Closed Co', companyType: 'client', status: 'archived' },
  ]
  assert.deepEqual(activeCompanies(list).map((c) => c.name), ['Acme', 'Open Co'])
  assert.deepEqual(activeCompanies([]), [])
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

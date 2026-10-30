// What the company fields do with the names: the hint for a new one (companyHint, public/js/dom-utils.js) and
// the suggestions, which are only the active companies (activeCompanyNames, public/js/companies.js).
// Run with: node --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

const { companyHint, companyCardLink, findCompany, openableLink, setNotice, typeConflict, typeFor } = await import('../../public/js/dom-utils.js')
const { activeCompanies, companyCounts, inTab, matchesSearch, statusTag, tabForCompany, tabForSearch } = await import('../../public/js/companies.js')

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

test('the tabs count the active and the archived companies', () => {
  const list = [{ status: 'active' }, { status: 'archived' }, { status: 'active' }, { status: 'archived' }, { status: 'archived' }]
  assert.deepEqual(companyCounts(list), { active: 2, archived: 3 })
  assert.deepEqual(companyCounts([]), { active: 0, archived: 0 })
})

test('a company is listed under the tab of its status', () => {
  assert.deepEqual(['active', 'archived', null].map((key) => inTab({ status: 'archived' }, key)), [false, true, true])
  assert.deepEqual(['active', 'archived', null].map((key) => inTab({ status: 'active' }, key)), [true, false, true])
})

test('the tag of an archived company says how it was closed, with the emoji of the event and a text in its color', () => {
  const tag = (closedBy) => statusTag({ status: 'archived', closedBy })
  const looks = (closedBy) => [tag(closedBy).emoji, tag(closedBy).text]
  assert.deepEqual(looks('ghosted'), ['👻', 'Ghosted'])
  assert.deepEqual(looks('rejection'), ['❌', 'Rejected'])
  assert.deepEqual(looks('red_flag'), ['🚩', 'Red flag'])
  assert.deepEqual(looks('on_hold'), ['⏸️', 'On hold'])
  assert.deepEqual(looks('offer'), ['🎉', 'Offer'])
  assert.deepEqual(looks(null), ['👻', 'Ghosted'])  // an archive by hand is the default
  assert.equal(tag('rejection').classes, 'bg-gray-800 text-red-400')  // the capsule is always the dark one; the text has the color
  assert.equal(tag('ghosted').classes, 'bg-gray-800 text-gray-300')  // whitish gray, like the ghost
  assert.deepEqual(statusTag({ status: 'active', closedBy: null }), { emoji: '', text: 'Active', classes: 'bg-gray-800 text-emerald-400' })
})

test('the search keeps the names that have what is typed, ignoring case and accents', () => {
  assert.ok(matchesSearch('Hire Hangar', 'hang'))
  assert.ok(matchesSearch('Café & Co', 'CAFE'))
  assert.ok(matchesSearch('Silver.dev', ' silver '))
  assert.ok(matchesSearch('Acme', ''))  // nothing typed lists everything
  assert.ok(!matchesSearch('Acme', 'beta'))
})

test('an application link is opened as a web address or as an email, and nothing else is', () => {
  assert.equal(openableLink(' https://jobs.example/x?id=1 '), 'https://jobs.example/x?id=1')
  assert.equal(openableLink('http://jobs.example'), 'http://jobs.example')
  assert.equal(openableLink('jobs@example.com'), 'mailto:jobs@example.com')
  assert.equal(openableLink('mailto:jobs@example.com'), 'mailto:jobs@example.com')
  for (const nothing of ['', '   ', null, undefined, 'javascript:alert(1)', 'data:text/html,hi', 'file:///etc/passwd', 'jobs.example/x', 'https://a b', 'two words']) {
    assert.equal(openableLink(nothing), null, String(nothing))
  }
})

test('a typed name picks the Active or Archived tab it is found in', () => {
  const list = [
    { name: 'Acme', status: 'active' },
    { name: 'Beta Corp', status: 'archived' },
    { name: 'Beta Labs', status: 'active' },
  ]
  assert.equal(tabForSearch(list, 'corp', 'active'), 'archived')  // only archived has it
  assert.equal(tabForSearch(list, 'acme', 'archived'), 'active')
  assert.equal(tabForSearch(list, 'beta', 'active'), 'active')  // the tab already has a match: it stays
  assert.equal(tabForSearch(list, 'zzz', 'archived'), 'archived')  // nowhere: it stays
  assert.equal(tabForSearch(list, '', 'archived'), 'archived')  // nothing typed
  assert.equal(tabForSearch(list, 'corp', null), null)  // showing everything already
})

test('a company is opened in the tab it is in', () => {
  assert.equal(tabForCompany({ status: 'archived' }, 'active'), 'archived')
  assert.equal(tabForCompany({ status: 'active' }, 'archived'), 'active')
  assert.equal(tabForCompany({ status: 'archived' }, 'archived'), 'archived')
  assert.equal(tabForCompany({ status: 'archived' }, null), null)  // showing everything
})

test('the arrow next to a company goes to its card in Companies, else nowhere', () => {
  assert.equal(companyCardLink({ id: 'acme', name: 'Acme' }), '#companies/acme')
  assert.equal(companyCardLink({ id: 'a b/c', name: 'Odd' }), '#companies/a%20b%2Fc')
  assert.equal(companyCardLink(undefined), null)
  assert.equal(companyCardLink(null), null)
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

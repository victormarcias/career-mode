// The "+ Application" form's rules and what it writes (public/js/application-form.js), with a fake API.
// Run with: node --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

const { applicationCompanyHint, buildNotes, isCompanyHome, isRecruiterProfile, linkedinUrl, parseRecruiters, saveApplication, splitRecruiters, validateApplication } = await import(
  '../../public/js/application-form.js'
)

const complete = {
  type: 'email_apply',
  company: 'Northwind Staffing',
  companyHome: 'https://www.linkedin.com/company/northwind-staffing/home/',
  recruiters: 'https://www.linkedin.com/in/jane-recruiter/',
  agency: true,
  website: '',
  notes: '',
  link: '',
}
const now = new Date(2026, 9, 9, 8, 5) // 9 Oct 2026, 08:05 local

function fakeApi() {
  const calls = []
  return {
    calls,
    create: async (collection, body) => {
      calls.push(['create', collection, body])
      return { id: collection === 'events' ? 'e1' : 'made-' + body.name.toLowerCase().replace(/\W+/g, '-'), ...body }
    },
    patch: async (collection, id, body) => {
      calls.push(['patch', collection, id, body])
      return { id, ...body }
    },
  }
}

test('LinkedIn addresses: the company page and the profile are told apart, and a bare prefix is not enough', () => {
  assert.ok(isCompanyHome('https://www.linkedin.com/company/northwind-staffing/home/'))
  assert.ok(isCompanyHome('https://linkedin.com/school/mit'))
  assert.ok(!isCompanyHome('https://www.linkedin.com/'))
  assert.ok(!isCompanyHome('https://www.linkedin.com/in/jane-recruiter/'))
  assert.ok(!isCompanyHome('https://evil.example/company/x'))
  assert.ok(!isCompanyHome('https://linkedin.com.evil.example/company/x'))
  assert.ok(isRecruiterProfile('https://www.linkedin.com/in/jane-recruiter/'))
  assert.ok(!isRecruiterProfile('https://www.linkedin.com/'))
  assert.ok(!isRecruiterProfile('https://www.linkedin.com/company/x'))
  assert.ok(!isRecruiterProfile('not a url'))
})

test('the LinkedIn fields take the whole link, and one without https:// is completed', () => {
  assert.equal(linkedinUrl(' https://www.linkedin.com/in/someone '), 'https://www.linkedin.com/in/someone')
  assert.equal(linkedinUrl('linkedin.com/in/someone'), 'https://www.linkedin.com/in/someone')
  assert.equal(linkedinUrl('www.linkedin.com/company/x/'), 'https://www.linkedin.com/company/x/')
  assert.equal(linkedinUrl('company/x'), 'company/x')
  assert.equal(linkedinUrl('  '), '')
})

test('the mandatory fields are checked in order, and a complete form passes', () => {
  assert.equal(validateApplication(complete), null)
  assert.match(validateApplication({ ...complete, type: '' }), /type/i)
  assert.match(validateApplication({ ...complete, type: 'web' }), /email, passive or web/)
  assert.match(validateApplication({ ...complete, company: '  ' }), /company name/i)
  assert.match(validateApplication({ ...complete, companyHome: 'https://www.linkedin.com/' }), /Company Home/)
  assert.match(validateApplication({ ...complete, companyHome: '' }), /Company Home is required/)
  assert.match(validateApplication({ ...complete, recruiters: 'https://www.linkedin.com/' }), /Each recruiter/)
  assert.match(validateApplication({ ...complete, recruiters: 'https://www.linkedin.com/company/x' }), /Each recruiter/)
  assert.match(validateApplication({ ...complete, companyHome: 'company/northwind-staffing' }), /Company Home/)  // a path alone is not a link
  assert.equal(validateApplication({ ...complete, companyHome: 'linkedin.com/company/northwind-staffing', recruiters: 'www.linkedin.com/in/jane-recruiter' }), null)
})

test('the recruiters are one per line, completed when pasted without https://, and not repeated', () => {
  assert.deepEqual(parseRecruiters('https://www.linkedin.com/in/a/\n\n linkedin.com/in/b \nhttps://www.linkedin.com/in/a/'), ['https://www.linkedin.com/in/a/', 'https://www.linkedin.com/in/b'])
  assert.deepEqual(parseRecruiters(''), [])
  assert.deepEqual(parseRecruiters(null), [])
})

test('the leading Recruiter: lines of the notes are split off for editing and put back by buildNotes', () => {
  assert.deepEqual(splitRecruiters('Recruiter: https://www.linkedin.com/in/x/\nTalent Pool form'), { recruiters: ['https://www.linkedin.com/in/x/'], rest: 'Talent Pool form' })
  assert.deepEqual(splitRecruiters('Recruiter: https://www.linkedin.com/in/x/\nRecruiter: https://www.linkedin.com/in/y/\nnotes\nmore'), { recruiters: ['https://www.linkedin.com/in/x/', 'https://www.linkedin.com/in/y/'], rest: 'notes\nmore' })
  assert.deepEqual(splitRecruiters('Recruiter: https://www.linkedin.com/in/x/'), { recruiters: ['https://www.linkedin.com/in/x/'], rest: '' })
  assert.deepEqual(splitRecruiters('Talent Pool form. Recruiter: Carolina'), { recruiters: [], rest: 'Talent Pool form. Recruiter: Carolina' })
  assert.deepEqual(splitRecruiters(null), { recruiters: [], rest: '' })
  const notes = 'Recruiter: https://www.linkedin.com/in/x/\nRecruiter: https://www.linkedin.com/in/y/\nsome notes'
  const { recruiters, rest } = splitRecruiters(notes)
  assert.equal(buildNotes(recruiters, rest), notes)
})

test('the Application link is required for a web application and optional for an email one', async () => {
  assert.match(validateApplication({ ...complete, type: 'web_form', link: '  ' }), /Application link is required/)
  assert.equal(validateApplication({ ...complete, type: 'web_form', link: 'https://jobs.example/1' }), null)
  assert.equal(validateApplication({ ...complete, type: 'email_apply', link: '' }), null)
  assert.equal(validateApplication({ ...complete, type: 'passive', link: '' }), null)
  const client = fakeApi()
  await assert.rejects(saveApplication({ ...complete, type: 'web_form', link: '' }, { agencies: [], clients: [], now }, client), /Application link is required/)
  assert.deepEqual(client.calls, [])
})

test('Company Home is optional without an agency and the recruiter is always optional, but a link that is given must be right', () => {
  assert.equal(validateApplication({ ...complete, agency: false, companyHome: '' }), null)
  assert.match(validateApplication({ ...complete, agency: false, companyHome: 'https://example.com/x' }), /Company Home must be/)
  assert.equal(validateApplication({ ...complete, recruiters: '' }), null)
  assert.equal(validateApplication({ ...complete, agency: false, companyHome: '', recruiters: '' }), null)
})

test('the recruiters lead the notes, one line each, and the typed notes follow', () => {
  assert.equal(buildNotes([], ''), '')
  assert.equal(buildNotes([], ' Just a note '), 'Just a note')
  assert.equal(buildNotes(['https://www.linkedin.com/in/x/'], ''), 'Recruiter: https://www.linkedin.com/in/x/')
  assert.equal(buildNotes(['https://www.linkedin.com/in/x/', 'https://www.linkedin.com/in/y/'], ' Talent pool form '), 'Recruiter: https://www.linkedin.com/in/x/\nRecruiter: https://www.linkedin.com/in/y/\nTalent pool form')
})

test('a new agency is created with its profile and recruiter, and the event gets the time of saving', async () => {
  const client = fakeApi()
  const typed = { ...complete, companyHome: ' https://www.linkedin.com/company/northwind-staffing/home/ ', recruiters: 'www.linkedin.com/in/jane-recruiter/' }
  await saveApplication({ ...typed, website: 'https://bajanearshore.com', notes: 'Talent Pool form', link: 'https://forms.example/x' }, { agencies: [], clients: [], now }, client)
  assert.deepEqual(client.calls, [
    [
      'create',
      'agencies',
      {
        name: 'Northwind Staffing',
        website: 'https://bajanearshore.com',
        linkedin: 'https://www.linkedin.com/company/northwind-staffing/home/',
        recruiters: ['https://www.linkedin.com/in/jane-recruiter/'],
      },
    ],
    [
      'create',
      'events',
      {
        date: '2026-10-09',
        time: '08:05',
        event: 'application',
        agencyId: 'made-northwind-staffing',
        clientId: null,
        notes: 'Recruiter: https://www.linkedin.com/in/jane-recruiter/\nTalent Pool form',
        jdUrl: 'https://forms.example/x',
        applyType: 'email_apply',
      },
    ],
  ])
})

test('several recruiters all go on a new agency and on the notes, and only the missing ones are added to an existing agency', async () => {
  const two = 'https://www.linkedin.com/in/one/\nhttps://www.linkedin.com/in/two/'
  const fresh = fakeApi()
  await saveApplication({ ...complete, recruiters: two }, { agencies: [], clients: [], now }, fresh)
  assert.deepEqual(fresh.calls[0][2].recruiters, ['https://www.linkedin.com/in/one/', 'https://www.linkedin.com/in/two/'])
  assert.equal(fresh.calls[1][2].notes, 'Recruiter: https://www.linkedin.com/in/one/\nRecruiter: https://www.linkedin.com/in/two/')

  const known = { id: 'northwind-staffing', name: 'Northwind Staffing', recruiters: ['https://www.linkedin.com/in/one/'] }
  const reused = fakeApi()
  await saveApplication({ ...complete, recruiters: two }, { agencies: [known], clients: [], now }, reused)
  assert.deepEqual(reused.calls[0].slice(0, 3), ['patch', 'agencies', 'northwind-staffing'])
  assert.deepEqual(reused.calls[0][3], { recruiters: ['https://www.linkedin.com/in/one/', 'https://www.linkedin.com/in/two/'] })
})

test('an agency that exists (ignoring case) is reused, and the recruiter is added only when missing', async () => {
  const known = { id: 'northwind-staffing', name: 'Northwind Staffing', recruiters: ['https://www.linkedin.com/in/someone/'] }
  const client = fakeApi()
  await saveApplication({ ...complete, company: 'northwind STAFFING' }, { agencies: [known], clients: [], now }, client)
  assert.deepEqual(client.calls.map((c) => c.slice(0, 3)), [['patch', 'agencies', 'northwind-staffing'], ['create', 'events', { ...client.calls[1][2] }]])
  assert.deepEqual(client.calls[0][3], { recruiters: ['https://www.linkedin.com/in/someone/', 'https://www.linkedin.com/in/jane-recruiter/'] })
  assert.equal(client.calls[1][2].agencyId, 'northwind-staffing')

  const again = fakeApi()
  const withRecruiter = { ...known, recruiters: ['https://www.linkedin.com/in/jane-recruiter/'] }
  await saveApplication(complete, { agencies: [withRecruiter], clients: [], now }, again)
  assert.deepEqual(again.calls.map((c) => c[1]), ['events'])
})

test('with "Agency" unticked the company is a direct client, and nothing is written for the agency', async () => {
  const client = fakeApi()
  await saveApplication({ ...complete, agency: false, company: 'Acme', type: 'email_apply' }, { agencies: [], clients: [], now }, client)
  assert.deepEqual(client.calls[0], [
    'create',
    'clients',
    { name: 'Acme', website: null, linkedin: 'https://www.linkedin.com/company/northwind-staffing/home/', viaAgencyId: null },
  ])
  const event = client.calls[1][2]
  assert.deepEqual([event.agencyId, event.clientId, event.applyType], [null, 'made-acme', 'email_apply'])
  assert.match(event.notes, /^Recruiter: /)

  const existing = fakeApi()
  await saveApplication({ ...complete, agency: false, company: 'ACME' }, { agencies: [], clients: [{ id: 'acme', name: 'Acme' }], now }, existing)
  assert.deepEqual(existing.calls.map((c) => c[1]), ['events'])
  assert.equal(existing.calls[0][2].clientId, 'acme')
})

test('without a recruiter nothing is added for one, and a direct client can have no LinkedIn at all', async () => {
  const agency = fakeApi()
  await saveApplication({ ...complete, recruiters: '', notes: 'n' }, { agencies: [], clients: [], now }, agency)
  assert.deepEqual(agency.calls[0][2].recruiters, [])
  assert.equal(agency.calls[1][2].notes, 'n')

  const known = { id: 'northwind-staffing', name: 'Northwind Staffing', recruiters: [] }
  const reused = fakeApi()
  await saveApplication({ ...complete, recruiters: '' }, { agencies: [known], clients: [], now }, reused)
  assert.deepEqual(reused.calls.map((c) => c[1]), ['events'])

  const direct = fakeApi()
  await saveApplication({ ...complete, agency: false, company: 'Acme', companyHome: '', recruiters: '' }, { agencies: [], clients: [], now }, direct)
  assert.deepEqual(direct.calls[0], ['create', 'clients', { name: 'Acme', website: null, linkedin: null, viaAgencyId: null }])
  assert.equal(direct.calls[1][2].notes, '')
})

test('a passive one logs a passive message with an agency and no link or apply type', async () => {
  const client = fakeApi()
  await saveApplication({ ...complete, type: 'passive', link: 'https://ignored.example' }, { agencies: [], clients: [], now }, client)
  const event = client.calls[1][2]
  assert.deepEqual([event.event, event.agencyId, event.clientId, event.jdUrl, event.applyType], ['passive_message', 'made-northwind-staffing', null, null, null])

  const direct = fakeApi()
  await assert.rejects(saveApplication({ ...complete, type: 'passive', agency: false }, { agencies: [], clients: [], now }, direct), /needs an agency/)
  assert.deepEqual(direct.calls, [])
})

test('an incomplete form writes nothing', async () => {
  const client = fakeApi()
  await assert.rejects(saveApplication({ ...complete, recruiters: 'https://www.linkedin.com/' }, { agencies: [], clients: [], now }, client), /Each recruiter/)
  assert.deepEqual(client.calls, [])
})

test('the company field says whether saving creates it, as an agency or as a direct client', () => {
  const lists = { agencies: [{ id: 'acme', name: 'Acme' }], clients: [{ id: 'solo', name: 'Solo Co' }] }
  assert.equal(applicationCompanyHint({ company: 'acme', agency: true }, lists), '')
  assert.equal(applicationCompanyHint({ company: 'Newco', agency: true }, lists), 'Will create the new agency "Newco".')
  assert.equal(applicationCompanyHint({ company: 'Newco', agency: false }, lists), 'Will create the new client "Newco".')
  assert.equal(applicationCompanyHint({ company: 'Solo Co', agency: false }, lists), '')
  assert.equal(applicationCompanyHint({ company: 'Acme', agency: false }, lists), 'Will create the new client "Acme".') // an agency is not a client
  assert.equal(applicationCompanyHint({ company: '  ', agency: true }, lists), '')
})

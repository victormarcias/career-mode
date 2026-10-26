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
  assert.equal(validateApplication({ ...complete, companyHome: '' }), null) // not required, not even for an agency
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

test('Company Home and the recruiter are always optional, but a link that is given must be right', () => {
  assert.equal(validateApplication({ ...complete, agency: true, companyHome: '' }), null)
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

const agency = (extra = {}) => ({ id: 'northwind-staffing', name: 'Northwind Staffing', companyType: 'agency', recruiters: [], ...extra })

test('a new agency is created with its profile and recruiter, and the event gets the time of saving', async () => {
  const client = fakeApi()
  const typed = { ...complete, companyHome: ' https://www.linkedin.com/company/northwind-staffing/home/ ', recruiters: 'www.linkedin.com/in/jane-recruiter/' }
  await saveApplication({ ...typed, website: 'https://bajanearshore.com', notes: 'Talent Pool form', link: 'https://forms.example/x' }, { companies: [], now }, client)
  assert.deepEqual(client.calls, [
    [
      'create',
      'companies',
      {
        name: 'Northwind Staffing',
        companyType: 'agency',
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
        companyId: 'made-northwind-staffing',
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
  await saveApplication({ ...complete, recruiters: two }, { companies: [], now }, fresh)
  assert.deepEqual(fresh.calls[0][2].recruiters, ['https://www.linkedin.com/in/one/', 'https://www.linkedin.com/in/two/'])
  assert.equal(fresh.calls[1][2].notes, 'Recruiter: https://www.linkedin.com/in/one/\nRecruiter: https://www.linkedin.com/in/two/')

  const reused = fakeApi()
  await saveApplication({ ...complete, recruiters: two }, { companies: [agency({ recruiters: ['https://www.linkedin.com/in/one/'] })], now }, reused)
  assert.deepEqual(reused.calls[0].slice(0, 3), ['patch', 'companies', 'northwind-staffing'])
  assert.deepEqual(reused.calls[0][3], { recruiters: ['https://www.linkedin.com/in/one/', 'https://www.linkedin.com/in/two/'] })
})

test('an agency that exists (ignoring case) is reused, and the recruiter is added only when missing', async () => {
  const known = agency({ recruiters: ['https://www.linkedin.com/in/someone/'] })
  const client = fakeApi()
  await saveApplication({ ...complete, company: 'northwind STAFFING' }, { companies: [known], now }, client)
  assert.deepEqual(client.calls.map((c) => c.slice(0, 3)), [['patch', 'companies', 'northwind-staffing'], ['create', 'events', { ...client.calls[1][2] }]])
  assert.deepEqual(client.calls[0][3], { recruiters: ['https://www.linkedin.com/in/someone/', 'https://www.linkedin.com/in/jane-recruiter/'] })
  assert.equal(client.calls[1][2].companyId, 'northwind-staffing')

  const again = fakeApi()
  await saveApplication(complete, { companies: [{ ...known, recruiters: ['https://www.linkedin.com/in/jane-recruiter/'] }], now }, again)
  assert.deepEqual(again.calls.map((c) => c[1]), ['events'])
})

test('with "Client" chosen the company is a direct client, and no recruiters go on it', async () => {
  const client = fakeApi()
  await saveApplication({ ...complete, agency: false, company: 'Acme', type: 'email_apply' }, { companies: [], now }, client)
  assert.deepEqual(client.calls[0], [
    'create',
    'companies',
    { name: 'Acme', companyType: 'client', website: null, linkedin: 'https://www.linkedin.com/company/northwind-staffing/home/' },
  ])
  const event = client.calls[1][2]
  assert.deepEqual([event.companyId, 'viaCompanyId' in event, event.applyType], ['made-acme', false, 'email_apply'])
  assert.match(event.notes, /^Recruiter: /)

  const existing = fakeApi()
  await saveApplication({ ...complete, agency: false, company: 'ACME' }, { companies: [{ id: 'acme', name: 'Acme', companyType: 'client' }], now }, existing)
  assert.deepEqual(existing.calls.map((c) => c[1]), ['events'])
  assert.equal(existing.calls[0][2].companyId, 'acme')
})

test('without a recruiter nothing is added for one, and a direct client can have no LinkedIn at all', async () => {
  const fresh = fakeApi()
  await saveApplication({ ...complete, recruiters: '', notes: 'n' }, { companies: [], now }, fresh)
  assert.deepEqual(fresh.calls[0][2].recruiters, [])
  assert.equal(fresh.calls[1][2].notes, 'n')

  const reused = fakeApi()
  await saveApplication({ ...complete, recruiters: '' }, { companies: [agency()], now }, reused)
  assert.deepEqual(reused.calls.map((c) => c[1]), ['events'])

  const direct = fakeApi()
  await saveApplication({ ...complete, agency: false, company: 'Acme', companyHome: '', recruiters: '' }, { companies: [], now }, direct)
  assert.deepEqual(direct.calls[0], ['create', 'companies', { name: 'Acme', companyType: 'client', website: null, linkedin: null }])
  assert.equal(direct.calls[1][2].notes, '')
})

test('a passive one logs a passive message with its company, and no link or apply type', async () => {
  const client = fakeApi()
  await saveApplication({ ...complete, type: 'passive', link: 'https://ignored.example' }, { companies: [], now }, client)
  const event = client.calls[1][2]
  assert.deepEqual([event.event, event.companyId, event.jdUrl, event.applyType], ['passive_message', 'made-northwind-staffing', null, null])

  const direct = fakeApi()
  await saveApplication({ ...complete, type: 'passive', agency: false }, { companies: [], now }, direct)
  assert.deepEqual([direct.calls[0][2].companyType, direct.calls[1][2].event, direct.calls[1][2].companyId], ['client', 'passive_message', 'made-northwind-staffing'])
})

test('a name that already is the other type is refused, so a company is never made twice', async () => {
  const client = fakeApi()
  await assert.rejects(saveApplication({ ...complete, agency: false }, { companies: [agency()], now }, client), /"Northwind Staffing" is already an agency/)
  assert.deepEqual(client.calls, [])
})

test('an incomplete form writes nothing', async () => {
  const client = fakeApi()
  await assert.rejects(saveApplication({ ...complete, recruiters: 'https://www.linkedin.com/' }, { companies: [], now }, client), /Each recruiter/)
  assert.deepEqual(client.calls, [])
})

test('the company field says whether saving creates it, as an agency or as a direct client', () => {
  const lists = { companies: [{ id: 'acme', name: 'Acme', companyType: 'agency' }, { id: 'solo', name: 'Solo Co', companyType: 'client' }] }
  assert.equal(applicationCompanyHint({ company: 'acme', agency: true }, lists), '')
  assert.equal(applicationCompanyHint({ company: 'Newco', agency: true }, lists), 'Will create the new agency "Newco".')
  assert.equal(applicationCompanyHint({ company: 'Newco', agency: false }, lists), 'Will create the new client "Newco".')
  assert.equal(applicationCompanyHint({ company: 'Solo Co', agency: false }, lists), '')
  assert.equal(applicationCompanyHint({ company: 'Acme', agency: false }, lists), '"Acme" is already an agency.') // an agency is not a client
  assert.equal(applicationCompanyHint({ company: '  ', agency: true }, lists), '')
})

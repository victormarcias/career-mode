import { api } from './api.js'
import { currentTime, toISODate } from './dates.js'
import { companyHint, findCompany, setNotice, typeConflict, typeConflictText, typeFor } from './dom-utils.js'
import { t } from './i18n.js'

// The form for an application sent by hand to a company that is new to the app: it asks for
// the company's LinkedIn page and the recruiter's profile, and creates the company (an agency,
// or a direct client, by its Agency or Client tag) together with the event. The date and time of
// the event are the moment the form is saved, not something to type.

// The LinkedIn fields take the whole link, as copied from the browser's address bar. One pasted
// without its https:// (or its www.) is completed, so linkedin.com/in/name works too.
export function linkedinUrl(value) {
  const link = value.trim()
  return /^(www\.)?linkedin\.com\//i.test(link) ? `https://www.${link.replace(/^www\./i, '')}` : link
}

// What the form logs: a recruiter who wrote first ("passive": a passive_message event), or an
// application sent by email or through a web form.
const TYPES = ['email_apply', 'passive', 'web_form']

// The path of a linkedin.com URL, or null when it isn't one.
function linkedinPath(value) {
  let url
  try {
    url = new URL(value.trim())
  } catch {
    return null
  }
  if (!['http:', 'https:'].includes(url.protocol)) return null
  return url.hostname.replace(/^www\./, '') === 'linkedin.com' ? url.pathname : null
}

// A company's page is /company/<name> (also /school/ and /showcase/); a person's is /in/<name>.
export const isCompanyHome = (value) => /^\/(company|school|showcase)\/[^/]+/.test(linkedinPath(value) ?? '')
export const isRecruiterProfile = (value) => /^\/in\/[^/]+/.test(linkedinPath(value) ?? '')

// The first problem with the form, as a sentence to show, or null when it can be saved. Company Home
// and the recruiters are never required (not everyone has a LinkedIn profile), but a link that is
// given has to be the right kind of address.
export function validateApplication(fields) {
  if (!TYPES.includes(fields.type)) return t('app.errType')
  if (fields.type === 'web_form' && !fields.link.trim()) return t('form.errLinkRequired')
  if (!fields.company.trim()) return t('app.errCompany')
  const home = linkedinUrl(fields.companyHome)
  if (home && !isCompanyHome(home)) return t('app.errHomeKind')
  if (parseRecruiters(fields.recruiters).some((r) => !isRecruiterProfile(r))) {
    return t('app.errRecruiters')
  }
  return null
}

// The Recruiters field takes one LinkedIn profile per line, like an agency's Recruiters field.
export function parseRecruiters(text) {
  return [...new Set((text ?? '').split(/\r?\n/).map(linkedinUrl).filter(Boolean))]
}

// The recruiters of this process, when there are any, go on the event, one `Recruiter:` line each at
// the top of its notes, as the apply skills do.
export function buildNotes(recruiters, notes) {
  return [...recruiters.map((r) => `Recruiter: ${r}`), notes.trim()].filter(Boolean).join('\n')
}

// The other way round, for editing: the recruiters on the leading `Recruiter:` lines, and the rest.
export function splitRecruiters(notes) {
  const lines = (notes ?? '').split('\n')
  const recruiters = []
  while (lines.length && /^Recruiter:/.test(lines[0])) {
    const value = lines.shift().replace(/^Recruiter:[ \t]*/, '').trim()
    if (value) recruiters.push(value)
  }
  return { recruiters, rest: lines.join('\n') }
}


// Creates what is new and returns the event. An existing company is found by name (ignoring case)
// and reused as it is, except that an agency gets the recruiters that are missing added to its list.
export async function saveApplication(fields, { companies, now = new Date() }, client = api) {
  const problem = validateApplication(fields)
  if (problem) throw new Error(problem)
  const companyType = fields.agency ? 'agency' : 'client'
  const conflict = typeConflict(companies, fields.company, companyType)
  if (conflict) throw new Error(typeConflictText(fields.company, conflict))

  const recruiters = parseRecruiters(fields.recruiters)
  const website = fields.website.trim() || null
  const profile = { name: fields.company.trim(), companyType, website, linkedin: linkedinUrl(fields.companyHome) || null }
  let companyId
  const found = findCompany(companies, fields.company)
  if (!found) {
    companyId = (await client.create('companies', fields.agency ? { ...profile, recruiters } : profile)).id
  } else {
    companyId = found.id
    const missing = fields.agency ? recruiters.filter((r) => !(found.recruiters ?? []).includes(r)) : []
    if (missing.length) await client.patch('companies', companyId, { recruiters: [...(found.recruiters ?? []), ...missing] })
  }

  const passive = fields.type === 'passive'
  return client.create('events', {
    date: toISODate(now),
    time: currentTime(now),
    event: passive ? 'passive_message' : 'application',
    companyId,
    notes: buildNotes(recruiters, fields.notes),
    jdUrl: passive ? null : fields.link.trim() || null,
    applyType: passive ? null : fields.type,
  })
}

// What the form says under the company name: whether saving will create it, as an agency or as a direct client,
// or that the name is already the other tag.
export function applicationCompanyHint({ company, agency }, { companies }) {
  return companyHint(companies, company, agency ? 'agency' : 'client')
}

// ---------- The form itself ----------

export function initApplicationForm({ getCompanies }) {
  const overlay = document.getElementById('app-overlay')
  const form = document.getElementById('app-form')
  const errorEl = document.getElementById('app-error')
  const submitBtn = document.getElementById('app-submit')
  const field = (id) => document.getElementById(`app-${id}`)

  const openButton = document.getElementById('new-application-btn')

  function open() {
    openButton.classList.add('active') // pressed while its form is open
    form.reset()
    syncType()
    setNotice(errorEl, '')
    overlay.classList.remove('hidden')
    overlay.classList.add('flex')
    requestAnimationFrame(() => form.classList.add('is-open'))
    field('type').focus()
  }

  function close() {
    openButton.classList.remove('active')
    form.classList.remove('is-open')
    setTimeout(() => {
      overlay.classList.add('hidden')
      overlay.classList.remove('flex')
    }, 150)
  }

  // A passive message has no link.
  function syncType() {
    const passive = field('type').value === 'passive'
    document.getElementById('app-link-wrap').classList.toggle('hidden', passive)
    // The Application link is required for a web application, and optional for an email one.
    const web = field('type').value === 'web_form'
    field('link').required = web
    document.getElementById('app-link-optional').classList.toggle('hidden', web)
    document.getElementById('app-link-req').classList.toggle('hidden', !web)
    syncCompanyType()
  }

  function syncCompanyType() {
    updateCompanyHint()
  }

  // Says under the company which name is new (it will be created as an agency, or as a direct client).
  function updateCompanyHint() {
    setNotice(
      document.getElementById('app-company-hint'),
      applicationCompanyHint({ company: field('company').value, agency: field('company-type').value === 'agency' }, { companies: getCompanies() }),
    )
  }

  document.getElementById('new-application-btn').addEventListener('click', open)
  document.getElementById('app-cancel').addEventListener('click', close)
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close()
  })
  field('company-type').addEventListener('change', syncCompanyType)
  // Typing the name of a company that exists is picking it: its tag follows.
  const pickCompany = () => {
    field('company-type').value = typeFor(getCompanies(), field('company').value, field('company-type').value)
    syncCompanyType()
  }
  field('company').addEventListener('input', pickCompany)
  field('company').addEventListener('change', pickCompany)
  field('type').addEventListener('change', syncType)

  form.addEventListener('submit', async (e) => {
    e.preventDefault()
    setNotice(errorEl, '')
    submitBtn.disabled = true
    submitBtn.textContent = t('form.saving')
    try {
      await saveApplication(
        {
          type: field('type').value,
          company: field('company').value,
          companyHome: field('home').value,
          recruiters: field('recruiter').value,
          agency: field('company-type').value === 'agency',
          website: field('website').value,
          notes: field('notes').value,
          link: field('link').value,
        },
        { companies: getCompanies() },
      )
      close()
    } catch (err) {
      setNotice(errorEl, err.message)
    } finally {
      submitBtn.disabled = false
      submitBtn.textContent = t('common.save')
    }
  })
}

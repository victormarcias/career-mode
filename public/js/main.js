import { api, subscribe } from './api.js'
import { EVENT_TYPES, EVENT_LABELS, EVENT_COLORS, EVENT_COLOR_HIGHLIGHT } from './events.js'
import { startOfWeek, addDays, formTime, toISODate, formatDayLabel, formatWeekNumber, formatWeekRange, currentOrNextBusinessWeekStart } from './dates.js'
import { companyHint, escapeHtml, findCompany, pendingLabel, setNotice, slideTransition, typeConflict, typeConflictText, typeFor } from './dom-utils.js'
import { renderOutreach, detectApplyType } from './outreach.js'
import { initPending, renderPending } from './pending.js'
import { initEntityEditForm } from './entity-edit.js'
import { buildNotes, initApplicationForm, parseRecruiters, splitRecruiters } from './application-form.js'
import { activeCompanies, renderCompanies, setStatusFilter } from './companies.js'
import { generateWeeklyReport, hideWeeklyReport, isWeeklyReportOpen, refreshWeeklyReport } from './weekly-report.js'
import { initFollowUp, renderFollowUp } from './follow-up.js'
import { renderSettings } from './settings.js'
import { renderProfile } from './profile-view.js'
import { initCalendarSync, refreshSyncButton } from './calendar-sync.js'
import { initI18n, t } from './i18n.js'

// ---------- App state ----------
let weekStart = currentOrNextBusinessWeekStart(new Date())
let applications = []
let companiesMap = new Map()
let appInitialized = false
let applicationsLoaded = false
let companiesLoaded = false

// Groups a day's pills by event type (in EVENT_TYPES' own order) instead of
// interleaving them by time — an event type not in that list sorts last.
const EVENT_TYPE_ORDER = new Map(EVENT_TYPES.map((t, i) => [t, i]))

function spinnerHtml() {
  return '<div class="flex justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-gray-700 border-t-gray-300"></div></div>'
}

function initApp() {
  if (appInitialized) return
  appInitialized = true

  document.getElementById('prev-week').addEventListener('click', () => navigateWeek(-7, 'right'))
  document.getElementById('next-week').addEventListener('click', () => navigateWeek(7, 'left'))
  document.getElementById('today').addEventListener('click', goToToday)

  document.getElementById('new-event-btn').addEventListener('click', () => openForm())
  document.getElementById('filter-active-btn').addEventListener('click', () => setStatusFilter('active'))
  document.getElementById('filter-archived-btn').addEventListener('click', () => setStatusFilter('archived'))
  document.getElementById('f-event').addEventListener('change', updateTypeFields)
  document.getElementById('f-apply-type').addEventListener('change', updateTypeFields)
  document.getElementById('f-company').addEventListener('input', pickCompany)
  document.getElementById('f-company').addEventListener('change', pickCompany)
  document.getElementById('f-company-type').addEventListener('change', updateCompanyType)
  document.getElementById('f-via').addEventListener('input', updateCompanyHint)
  // Pressed once it opens the report, pressed again it folds it away.
  document.getElementById('weekly-report-btn').addEventListener('click', () => {
    if (isWeeklyReportOpen()) hideWeeklyReport('right')
    else generateWeeklyReport(applications, weekStart)
  })
  document.getElementById('form-cancel').addEventListener('click', closeForm)
  document.getElementById('form-delete').addEventListener('click', handleFormDelete)
  document.getElementById('form-overlay').addEventListener('click', (e) => {
    if (e.target.id === 'form-overlay') closeForm()
  })
  document.getElementById('event-form').addEventListener('submit', handleFormSubmit)

  document.querySelectorAll('.nav-item').forEach((btn) => {
    btn.addEventListener('click', () => {
      location.hash = btn.dataset.nav
    })
  })
  initPending({ getApplications: () => applications, onOpenEvent: (app) => (location.hash = `calendar~${app.id}`) })
  initEntityEditForm()
  initApplicationForm({ getCompanies: () => Array.from(companiesMap.values()) })
  initFollowUp(companiesDeps)
  initCalendarSync({ getWeekStart: () => weekStart, getCompanies: () => Array.from(companiesMap.values()) })

  subscribe('events', (rows) => {
    applications = rows
    applicationsLoaded = true
    refreshWeeklyReport(applications, weekStart)
    renderDatalists()
    if (currentSection() === 'calendar') renderWeek()
    if (currentSection() === 'pending') renderPending(applications)
    if (currentSection() === 'companies') handleRoute()
    maybeOpenEvent()
  })
  subscribe('companies', (rows) => {
    companiesMap = new Map(rows.map((c) => [c.id, c]))
    companiesLoaded = true
    renderDatalists()
    if (currentSection() === 'companies') handleRoute()
    if (currentSection() === 'calendar') renderWeek()  // a company's name or type can change what an event says
  })
  window.addEventListener('hashchange', handleRoute)
  handleRoute()
}

// These types are not picked in this form
const LOCKED_TYPES = ['application', 'passive_message', 'archive', 'pending']

// The types are listed A-Z by name. An event of one of the locked types that is being edited keeps its
// type: the select offers only that one (and is disabled; for an application it is also hidden, the Type
// replaces it).
function fillEventSelect(lockedType) {
  const select = document.getElementById('f-event')
  select.innerHTML = [...EVENT_TYPES, 'pending']
    .filter((t) => (lockedType ? t === lockedType : !LOCKED_TYPES.includes(t)))
    .sort((a, b) => EVENT_LABELS[a].label.localeCompare(EVENT_LABELS[b].label))
    .map((t) => `<option value="${t}">${EVENT_LABELS[t].emoji} ${EVENT_LABELS[t].label}</option>`)
    .join('')
}

// The company suggestions come from the lists the page already has, and are only the active companies (a
// client is active or not by its events, so this runs again when they change). Company has both, each
// with its tag; Via agency has the agencies.
function renderDatalists() {
  const active = activeCompanies(Array.from(companiesMap.values()))
  const options = (list, label) =>
    list.map((c) => `<option value="${escapeHtml(c.name)}"${label ? ` label="${t(c.companyType === 'agency' ? 'form.agency' : 'form.client')}"` : ''}>`).join('')
  document.getElementById('agency-list').innerHTML = options(active.filter((c) => c.companyType === 'agency'))
  document.getElementById('company-list').innerHTML = options(active, true)
}

// ---------- Router ----------
let pendingEventId = null

function parseHash() {
  const raw = location.hash.slice(1) || 'calendar'
  const [pathPart, anchor] = raw.split('~')
  if (pathPart === 'outreach' || pathPart.startsWith('outreach/')) {
    return { section: 'outreach', tab: pathPart.slice('outreach/'.length) || null }
  }
  // `companies/<id>` opens that company's card; the older `agencies/<id>` and `clients/<id>` links still do
  const company = pathPart.match(/^(?:companies|agencies|clients)(?:\/(.+))?$/)
  if (company) return { section: 'companies', openCompanyId: company[1] ?? null }
  if (pathPart === 'follow-up') {
    return { section: 'follow-up' }
  }
  if (pathPart === 'pending') {
    return { section: 'pending' }
  }
  if (pathPart === 'settings') {
    return { section: 'settings' }
  }
  if (pathPart === 'profile') {
    return { section: 'profile' }
  }
  return { section: 'calendar', anchor }
}

function currentSection() {
  return parseHash().section
}

function handleRoute() {
  const parsed = parseHash()
  const { section } = parsed

  document.getElementById('view-calendar').classList.toggle('hidden', section !== 'calendar')
  document.getElementById('view-outreach').classList.toggle('hidden', section !== 'outreach')
  document.getElementById('view-companies').classList.toggle('hidden', section !== 'companies')
  document.getElementById('view-follow-up').classList.toggle('hidden', section !== 'follow-up')
  document.getElementById('view-pending').classList.toggle('hidden', section !== 'pending')
  document.getElementById('view-settings').classList.toggle('hidden', section !== 'settings')
  document.getElementById('view-profile').classList.toggle('hidden', section !== 'profile')

  updateSidebarActive(section)

  if (section === 'calendar') {
    refreshSyncButton() // the calendar may have been set (or removed) in Settings since the last visit
    if (parsed.anchor) pendingEventId = parsed.anchor
    renderWeek()
    maybeOpenEvent()
  } else if (section === 'outreach') {
    renderOutreach(parsed.tab)
  } else if (section === 'companies') {
    renderCompanies(parsed, companiesDeps())
  } else if (section === 'follow-up') {
    renderFollowUp()
  } else if (section === 'pending') {
    renderPending(applications)
  } else if (section === 'settings') {
    renderSettings()
  } else if (section === 'profile') {
    renderProfile()
  }
}

function companiesDeps() {
  // An event clicked in a company's timeline or in Follow Up is opened in the Calendar.
  return { applications, companiesMap, companiesLoaded, onOpenEvent: (app) => (location.hash = `calendar~${app.id}`) }
}

function updateSidebarActive(section) {
  document.querySelectorAll('.nav-item').forEach((btn) => btn.classList.remove('active'))
  const btn = document.querySelector(`.nav-item[data-nav="${section}"]`)
  if (btn) btn.classList.add('active')
}

// The route calendar~<id> shows the week of that event and opens its edit form.
function maybeOpenEvent() {
  if (!pendingEventId || !applications.length) return
  const app = applications.find((a) => a.id === pendingEventId)
  if (app) {
    // A queued link is not in the week (the Pending page lists it), so there is no week to go to.
    if (app.event !== 'pending') {
      weekStart = startOfWeek(new Date(app.date + 'T00:00:00'))
      hideWeeklyReport()
      renderWeek()
    }
    openForm(app)
  }
  pendingEventId = null
}

// ---------- Calendar rendering ----------
const WEEK_SLIDE_MS = 180
const TODAY_FADE_MS = 120

function goToToday() {
  const todayWeekStart = currentOrNextBusinessWeekStart(new Date())
  if (isWeeklyReportOpen()) {
    // The report is on screen: show this week's grid in its place.
    weekStart = todayWeekStart
    renderWeek()
    hideWeeklyReport('right')
    return
  }
  if (toISODate(todayWeekStart) === toISODate(weekStart)) return

  const grid = document.getElementById('week-grid')
  grid.classList.add('fading', 'fade-out')
  setTimeout(() => {
    weekStart = todayWeekStart
    hideWeeklyReport()
    renderWeek()
    grid.classList.remove('fade-out')
    setTimeout(() => grid.classList.remove('fading'), TODAY_FADE_MS)
  }, TODAY_FADE_MS)
}

function navigateWeek(days, direction) {
  if (isWeeklyReportOpen()) {
    // The report is on screen: show the other week's grid in its place.
    weekStart = addDays(weekStart, days)
    renderWeek()
    hideWeeklyReport(direction)
    return
  }
  const grid = document.getElementById('week-grid')
  slideTransition(
    grid,
    direction,
    () => {
      weekStart = addDays(weekStart, days)
      hideWeeklyReport()
      renderWeek()
    },
    WEEK_SLIDE_MS,
  )
}

// The label of an event is "Agency → Client" when it came through an agency, else the company's name: the
// server derives it (companyLabel), so it can never drift out of sync with the real records.
function pillLabel(app) {
  return app.companyLabel ?? ''
}

// The pills of one agency light up together: the events of the agency itself and those of its clients that came through it.
function agencyKey(app) {
  return app.viaCompanyId || (companiesMap.get(app.companyId)?.companyType === 'agency' ? app.companyId : '')
}

// Archives are not shown in the Calendar (an archive is how a company is closed, not something that
// happened on a day; one is still opened from the company's timeline, which goes to its week). Neither are
// queued links (`pending`): they are not on a day either, and the Pending page lists them.
function shownInCalendar(app) {
  return app.event !== 'archive' && app.event !== 'pending'
}


function renderWeek() {
  // This Week is on while the week shown is the current one.
  document.getElementById('today').classList.toggle('active', toISODate(weekStart) === toISODate(currentOrNextBusinessWeekStart(new Date())))
  document.getElementById('week-label').textContent = formatWeekNumber(weekStart)
  document.getElementById('week-range').textContent = formatWeekRange(weekStart)
  const grid = document.getElementById('week-grid')
  grid.innerHTML = ''

  if (!applicationsLoaded) {
    grid.innerHTML = `<div class="col-span-5">${spinnerHtml()}</div>`
    return
  }

  const byDate = new Map()
  for (const app of applications.filter(shownInCalendar)) {
    const list = byDate.get(app.date) ?? []
    list.push(app)
    byDate.set(app.date, list)
  }

  for (let i = 0; i < 5; i++) {
    const day = addDays(weekStart, i)
    const iso = toISODate(day)
    const isToday = iso === toISODate(new Date())
    const events = (byDate.get(iso) ?? []).slice().sort((a, b) => {
      const orderA = EVENT_TYPE_ORDER.get(a.event) ?? EVENT_TYPES.length
      const orderB = EVENT_TYPE_ORDER.get(b.event) ?? EVENT_TYPES.length
      if (orderA !== orderB) return orderA - orderB
      return (a.time ?? '99:99').localeCompare(b.time ?? '99:99')
    })

    const col = document.createElement('div')
    col.className = `day-column rounded-2xl border p-3 ${
      isToday ? 'border-blue-700 bg-blue-950/30' : 'border-gray-800 bg-gray-900'
    }`

    const heading = document.createElement('div')
    heading.className = 'mb-3 text-xs font-medium uppercase tracking-wide text-gray-400'
    heading.textContent = formatDayLabel(day)
    col.appendChild(heading)

    const list = document.createElement('div')
    list.className = 'space-y-2'

    for (const app of events) {
      const meta = EVENT_LABELS[app.event] ?? { emoji: '•', label: app.event }
      const color = EVENT_COLORS[app.event] ?? 'bg-gray-100 text-gray-800'
      const pill = document.createElement('button')
      pill.className = `event-pill block w-full rounded-2xl px-3 py-2 text-left text-sm ${color}`
      pill.innerHTML = `
        ${app.time ? `<div class="text-[10px] font-semibold opacity-70">${app.time}</div>` : ''}
        <div class="flex items-center gap-1.5">
          <span>${meta.emoji}</span>
          <span class="truncate font-medium">${escapeHtml(pillLabel(app))}</span>
        </div>
      `
      const group = agencyKey(app)
      pill.dataset.agencyId = group
      pill.dataset.colorLight = color
      pill.addEventListener('click', () => openForm(app))
      if (group) {
        pill.addEventListener('mouseenter', () => {
          const matches = grid.querySelectorAll(`.event-pill[data-agency-id="${group}"]`)
          if (matches.length > 1) {
            matches.forEach((el) => {
              el.classList.add('agency-highlight')
              el.classList.remove(...el.dataset.colorLight.split(' '))
              el.classList.add(...EVENT_COLOR_HIGHLIGHT.split(' '))
            })
          }
        })
        pill.addEventListener('mouseleave', () => {
          grid.querySelectorAll(`.event-pill[data-agency-id="${group}"]`).forEach((el) => {
            el.classList.remove('agency-highlight')
            el.classList.remove(...EVENT_COLOR_HIGHLIGHT.split(' '))
            el.classList.add(...el.dataset.colorLight.split(' '))
          })
        })
      }
      list.appendChild(pill)
    }

    col.appendChild(list)
    grid.appendChild(col)
  }
}

// ---------- Update form ----------
// Set while editing an existing event instead of creating a new one.
let editingAppId = null

// An application or a passive message is edited with one Type (Email, Passive or Web) in place of the
// Event select, the way "+ Application" logs them. Set by openForm.
let typeDrivenEdit = false

// A queued link being edited: it has no company yet, so the form is only its date, time, link and notes.
let pendingEdit = false

// What the form says it logs: 'passive_message' or 'application' from the Type, else the Event select.
function currentEvent() {
  if (!typeDrivenEdit) return document.getElementById('f-event').value
  return document.getElementById('f-apply-type').value === 'passive' ? 'passive_message' : 'application'
}

// The title of an edit form is "{Company} → {Event}", the event following what the form would save: the
// Type of an application or a passive message, else the Event select. A new event has no company yet.
let editingCompany = ''

function companyTitle(app) {
  if (app.event === 'pending') return pendingLabel(app)
  return app.companyLabel || '—'
}

function eventFormTitle() {
  if (!editingAppId) return t('form.titleUpdate')
  const event = currentEvent()
  const name = typeDrivenEdit && event === 'passive_message' ? t('app.typePassive') : (EVENT_LABELS[event]?.label ?? event)
  return `${editingCompany} → ${name}`
}

// The Application link belongs to an application being edited (or a queued link), not to any other
// event, and a passive message has none. An application of type Web must have it.
function updateTypeFields() {
  document.getElementById('event-form-title').textContent = eventFormTitle()
  const hasLink = pendingEdit || (typeDrivenEdit && currentEvent() !== 'passive_message')
  document.getElementById('f-jd-wrap').classList.toggle('hidden', !hasLink)
  const web = typeDrivenEdit && document.getElementById('f-apply-type').value === 'web_form'
  document.getElementById('f-jd').required = web
  document.getElementById('f-jd-optional').classList.toggle('hidden', web)
  document.getElementById('f-jd-req').classList.toggle('hidden', !web)
}

// Says under the company which of the typed names are new, so a typo doesn't quietly create a company, and when
// the name already is the other type.
function updateCompanyHint() {
  setNotice(
    document.getElementById('f-company-hint'),
    companyHint(
      Array.from(companiesMap.values()),
      document.getElementById('f-company').value,
      document.getElementById('f-company-type').value,
      document.getElementById('f-via').value,
    ),
  )
}

// The agency a client comes through is asked only for a client.
function updateCompanyType() {
  document.getElementById('f-via').classList.toggle('hidden', document.getElementById('f-company-type').value !== 'client')
  updateCompanyHint()
}

// Typing the name of a company that exists is picking it: its type follows, and a client brings the agency
// it comes through, or empties the field when it has none.
function pickCompany() {
  const companies = Array.from(companiesMap.values())
  const name = document.getElementById('f-company').value
  const typeSelect = document.getElementById('f-company-type')
  typeSelect.value = typeFor(companies, name, typeSelect.value)
  const company = typeSelect.value === 'client' ? findCompany(companies, name) : null
  if (company) document.getElementById('f-via').value = companiesMap.get(company.viaCompanyId)?.name ?? ''
  updateCompanyType()
}

// The Type select of an application being edited. An application with no type yet shows a blank one.
function fillApplyType(current) {
  const options = [['email_apply', t('app.typeEmail')], ['passive', t('app.typePassive')], ['web_form', t('app.typeWeb')]]
  if (!current) options.unshift(['', '—'])
  const select = document.getElementById('f-apply-type')
  select.innerHTML = options.map(([value, label]) => `<option value="${value}">${label}</option>`).join('')
  select.value = current
}

function openForm(app = null) {
  editingAppId = app ? app.id : null
  editingCompany = app ? companyTitle(app) : ''
  document.getElementById('event-form').reset()
  const locked = app && ['application', 'archive', 'pending'].includes(app.event) ? app.event : null
  fillEventSelect(locked)
  document.getElementById('form-delete').classList.toggle('hidden', !app)
  document.getElementById('f-date').value = app ? app.date : toISODate(new Date())
  // A new event opens with the current time; an edit keeps the time the event has (the current one only if it has none).
  document.getElementById('f-time').value = formTime(app?.time)
  document.getElementById('f-event').value = app ? app.event : 'note'
  // An application, an archive or a queued link keeps its type.
  document.getElementById('f-event').disabled = Boolean(locked)
  // A queued link has no company: its form is the date, time, link and notes.
  pendingEdit = app?.event === 'pending'
  document.getElementById('f-company-wrap').classList.toggle('hidden', pendingEdit)

  const company = (app?.companyId && companiesMap.get(app.companyId)) || null
  document.getElementById('f-company').value = company?.name ?? ''
  document.getElementById('f-company-type').value = company?.companyType ?? 'agency'
  document.getElementById('f-via').value = (app?.viaCompanyId && companiesMap.get(app.viaCompanyId)?.name) || ''

  // An application or a passive message is edited by its Type, and has its recruiter, which is the
  // first line of its notes.
  typeDrivenEdit = Boolean(app && (app.event === 'application' || app.event === 'passive_message'))
  document.getElementById('f-event-wrap').classList.toggle('hidden', typeDrivenEdit)
  document.getElementById('f-apply-wrap').classList.toggle('hidden', !typeDrivenEdit)
  document.getElementById('f-recruiter-wrap').classList.toggle('hidden', !typeDrivenEdit)
  if (typeDrivenEdit) fillApplyType(app.event === 'passive_message' ? 'passive' : (app.applyType ?? detectApplyType(app.jdUrl) ?? ''))
  const { recruiters, rest } = typeDrivenEdit ? splitRecruiters(app.notes) : { recruiters: [], rest: app?.notes ?? '' }
  document.getElementById('f-recruiter').value = recruiters.join('\n')
  document.getElementById('f-notes').value = rest
  // A link is given when an application is logged (+ Application); this form only edits it.
  document.getElementById('f-jd').value = app?.jdUrl ?? ''
  updateTypeFields()
  updateCompanyType()
  setNotice(document.getElementById('form-error'), '')

  const overlay = document.getElementById('form-overlay')
  const card = document.getElementById('event-form')
  // + Update looks pressed only while it is the one that opened the form, not while an event is being edited.
  document.getElementById('new-event-btn').classList.toggle('active', !app)
  overlay.classList.remove('hidden')
  overlay.classList.add('flex')
  requestAnimationFrame(() => card.classList.add('is-open'))
}

function closeForm() {
  const overlay = document.getElementById('form-overlay')
  const card = document.getElementById('event-form')
  document.getElementById('new-event-btn').classList.remove('active')
  card.classList.remove('is-open')
  setTimeout(() => {
    overlay.classList.add('hidden')
    overlay.classList.remove('flex')
  }, 150)
}

async function handleFormSubmit(e) {
  e.preventDefault()
  const submitBtn = document.getElementById('form-submit')
  const errorEl = document.getElementById('form-error')
  setNotice(errorEl, '')
  submitBtn.disabled = true
  submitBtn.textContent = t('form.saving')

  try {
    const date = document.getElementById('f-date').value
    const event = currentEvent()
    const type = typeDrivenEdit ? document.getElementById('f-apply-type').value : null
    if (type === 'web_form' && !document.getElementById('f-jd').value.trim()) throw new Error(t('form.errLinkRequired'))
    const time = document.getElementById('f-time').value || null
    if (pendingEdit) {
      // A queued link: only its date, time, link and notes. The apply type follows the link.
      const link = document.getElementById('f-jd').value.trim() || null
      await api.patch('events', editingAppId, {
        date,
        time,
        notes: document.getElementById('f-notes').value.trim(),
        jdUrl: link,
        applyType: detectApplyType(link),
      })
      closeForm()
      return
    }
    const name = document.getElementById('f-company').value.trim()
    const companyType = document.getElementById('f-company-type').value
    // Every event but a new application (its own form) belongs to a company: an agency, or a client with the
    // agency it came through when it has one.
    if (!name) throw new Error(t('form.errPickCompany'))
    const companies = Array.from(companiesMap.values())
    const conflict = typeConflict(companies, name, companyType)
    if (conflict) throw new Error(typeConflictText(name, conflict))
    const viaName = companyType === 'client' ? document.getElementById('f-via').value.trim() : ''
    const viaConflict = viaName ? typeConflict(companies, viaName, 'agency') : null
    if (viaConflict) throw new Error(typeConflictText(viaName, viaConflict))
    let notes = document.getElementById('f-notes').value.trim()
    if (typeDrivenEdit) notes = buildNotes(parseRecruiters(document.getElementById('f-recruiter').value), notes)

    // An existing company is found by name (ignoring case) and reused; only a new one is created. Whether an
    // event archives or reactivates its company is derived from its events, so there is no status to write here.
    let viaCompanyId = null
    if (viaName) {
      const via = findCompany(companies, viaName)
      viaCompanyId = via ? via.id : (await api.create('companies', { name: viaName, companyType: 'agency' })).id
    }
    let companyId
    const existing = findCompany(companies, name)
    if (existing) {
      companyId = existing.id
      // With an agency the client is (re)pointed to it; without one the client is direct.
      if (companyType === 'client' && (existing.viaCompanyId ?? null) !== viaCompanyId) await api.patch('companies', existing.id, { viaCompanyId })
    } else {
      companyId = (await api.create('companies', viaCompanyId ? { name, companyType, viaCompanyId } : { name, companyType })).id
    }

    const payload = { date, time, event, companyId, viaCompanyId, notes }
    if (typeDrivenEdit) {
      // An application's link can be edited; a passive message has none. The Type of an application is
      // its apply type. Any other event leaves both as they are.
      payload.jdUrl = event === 'passive_message' ? null : document.getElementById('f-jd').value.trim() || null
      payload.applyType = event === 'passive_message' ? null : type || null
    }
    if (editingAppId) await api.patch('events', editingAppId, payload)
    else await api.create('events', payload)
    closeForm()
  } catch (err) {
    setNotice(errorEl, err.message)
  } finally {
    submitBtn.disabled = false
    submitBtn.textContent = t('common.save')
  }
}

async function handleFormDelete() {
  if (!editingAppId) return
  if (!confirm(t('form.confirmDelete'))) return
  const errorEl = document.getElementById('form-error')
  setNotice(errorEl, '')
  try {
    await api.remove('events', editingAppId)
    closeForm()
  } catch (err) {
    setNotice(errorEl, err.message)
  }
}

// ---------- Companies (agencies and clients): see companies.js ----------

await initI18n() // the texts are in public/locales; the language is the APP_LANGUAGE setting
initApp()

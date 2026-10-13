import { escapeHtml, renderNotes, fadeTransition, wireAccordion } from './dom-utils.js'
import { EVENT_LABELS, EVENT_COLORS, isClosingEvent } from './events.js'
import { openEntityEdit } from './entity-edit.js'
import { t } from './i18n.js'

let lastOpenId = null
let lastDeps = null

// null = no filter, show everything. 'active'/'archived' are mutually
// exclusive with each other, but neither is required — clicking the one
// that's already selected clears it back to null (show everything again).
// Defaults to 'active' so a fresh page load (or first visit to Companies)
// starts filtered to what's actually relevant, not a mixed active+archived list.
let statusFilterKey = 'active'

function matchesStatusFilter(archived) {
  if (statusFilterKey === null) return true
  return archived ? statusFilterKey === 'archived' : statusFilterKey === 'active'
}

// Re-renders in place with a fade (no slide) — a filter change isn't a "moved
// to a different section" the way switching tabs is.
export function setStatusFilter(key) {
  statusFilterKey = statusFilterKey === key ? null : key
  if (lastDeps) renderList(lastOpenId, lastDeps, 'fade')
}

// applicationLink can be a URL or a bare email address — turn the latter into a mailto: link.
function applicationLinkHref(link) {
  return link.includes('@') ? `mailto:${link}` : link
}

// Most recent first. A closing event (Rejection/Red Flag/On-hold/Offer) always wins a
// same-date tie regardless of its time — it's the actual last word on that
// application, whatever time it happens to carry (or none at all). Only
// among two events of the same "closing-ness" does time break the tie.
function byDateTimeDesc(a, b) {
  if (a.date !== b.date) return b.date.localeCompare(a.date)
  const aClosing = isClosingEvent(a.event)
  const bClosing = isClosingEvent(b.event)
  if (aClosing !== bClosing) return aClosing ? -1 : 1
  return (b.time || '00:00').localeCompare(a.time || '00:00')
}

function spinnerHtml() {
  return '<div class="flex justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-gray-700 border-t-gray-300"></div></div>'
}

// Preview of a note: the raw text is cut BEFORE rendering. Cutting the rendered HTML
// instead can slice through a tag (e.g. the <a href="..."> renderNotes builds from a
// URL) and leave it unclosed, which swallows every card that follows. The cut backs
// up to a word boundary so a URL is never left half-linked.
const NOTES_PREVIEW_CHARS = 300

function notesPreviewHtml(notes) {
  const text = notes ?? ''
  if (text.length <= NOTES_PREVIEW_CHARS) return renderNotes(text)
  const cut = /\s/.test(text[NOTES_PREVIEW_CHARS]) ? text.slice(0, NOTES_PREVIEW_CHARS) : text.slice(0, NOTES_PREVIEW_CHARS).replace(/\s\S*$/, '')
  return renderNotes(cut) + '…'
}

function timelineHtml(matches) {
  if (!matches.length) return `<p class="text-sm text-gray-500">${t('companies.noEvents')}</p>`
  return matches
    .slice()
    .sort(byDateTimeDesc)
    .map((app) => {
      const meta = EVENT_LABELS[app.event] ?? { emoji: '•', label: app.event }
      const color = EVENT_COLORS[app.event] ?? 'bg-gray-800 text-gray-200'
      return `
        <div class="timeline-row block w-full cursor-pointer rounded-xl border border-gray-700 bg-gray-800 p-3 text-left hover:border-gray-600" data-app-id="${app.id}" role="button" tabindex="0">
          <div class="mb-1 flex items-center gap-2 text-xs text-gray-500">
            <span class="rounded-full px-2 py-0.5 text-[11px] font-medium ${color}">${meta.emoji} ${meta.label}</span>
            <span>${app.date}${app.time ? ' · ' + app.time : ''}</span>
          </div>
          <p class="text-sm text-gray-300">${notesPreviewHtml(app.notes)}</p>
        </div>
      `
    })
    .join('')
}

// The Agency/Client tag next to a company's name. Exported so Check
// Applications shows the very same one.
export function kindTagHtml(kind) {
  const isAgency = kind === 'agency'
  return `<span class="rounded-full px-2 py-0.5 text-[10px] ${isAgency ? 'bg-blue-950 text-blue-300' : 'bg-violet-950 text-violet-300'}">${isAgency ? t('companies.agency') : t('companies.client')}</span>`
}

// Exported for follow-up.js, which reuses this exact card body
// (Website/LinkedIn/Recruiters/Application/Timeline) inside its own
// expandable results list — "the same card as Companies", not a rebuild.
export function agencyBodyHtml(a, matches) {
  const recruiters = a.recruiters?.length
    ? a.recruiters.map((url) => `<a href="${url}" target="_blank" rel="noreferrer" class="block text-blue-400 underline hover:text-blue-300">${url}</a>`).join('')
    : `<p class="text-gray-500">${t('companies.noRecruiters')}</p>`

  return `
    <p class="mb-4 text-sm leading-relaxed text-gray-300">${escapeHtml(a.type) || '—'}</p>
    <div class="mb-6 space-y-1 text-sm">
      <div><span class="text-gray-500">${t('companies.website')}:</span> ${a.website ? `<a href="${a.website}" target="_blank" rel="noreferrer" class="break-all text-blue-400 underline hover:text-blue-300">${a.website}</a>` : '—'}</div>
      <div><span class="text-gray-500">LinkedIn:</span> ${a.linkedin ? `<a href="${a.linkedin}" target="_blank" rel="noreferrer" class="break-all text-blue-400 underline hover:text-blue-300">${a.linkedin}</a>` : '—'}</div>
    </div>
    <h2 class="mb-2 text-sm font-medium text-gray-400">${t('companies.recruiters')}</h2>
    <div class="mb-6 space-y-1 text-sm">${recruiters}</div>
    ${
      a.applicationLink
        ? `<a href="${applicationLinkHref(a.applicationLink)}" target="_blank" rel="noreferrer" class="mb-6 inline-block rounded-full bg-gray-100 px-4 py-2 text-sm font-medium text-gray-900 hover:bg-white">${t('companies.application')} →</a>`
        : `<span class="mb-6 inline-block cursor-not-allowed rounded-full bg-gray-800 px-4 py-2 text-sm font-medium text-gray-500">${t('companies.application')} →</span>`
    }
    <h2 class="mb-2 mt-4 text-sm font-medium text-gray-400">${t('companies.timeline', { count: matches.length })}</h2>
    <div class="space-y-2">${timelineHtml(matches)}</div>
  `
}

function agencyCardHtml(a, applications, isOpen) {
  const matches = applications.filter((app) => app.agencyId === a.id)
  return `
    <div class="capsule" data-key="agency:${a.id}" data-open="${isOpen}">
      <div class="capsule-header">
        <button type="button" class="capsule-summary" aria-expanded="${isOpen}">
          <div class="flex w-full items-center gap-2">
            <span>🏢</span>
            <span class="font-medium text-gray-100">${escapeHtml(a.name)}</span>
            ${kindTagHtml('agency')}
            <span class="ml-auto rounded-full px-2 py-0.5 text-[10px] ${a.status === 'archived' ? 'bg-gray-800 text-red-400' : 'bg-gray-800 text-emerald-400'}">${a.status === 'archived' ? t('companies.statusArchived') : t('companies.statusActive')}</span>
          </div>
        </button>
        <button type="button" class="capsule-edit-btn agency-edit-btn rounded-full bg-gray-100 px-4 py-1 text-sm font-medium text-gray-900 hover:bg-white" data-id="${a.id}">${t('common.edit')}</button>
      </div>
      <div class="capsule-body-wrap">
        <div class="capsule-body">${agencyBodyHtml(a, matches)}</div>
      </div>
    </div>
  `
}

// Exported for follow-up.js (same reuse as agencyBodyHtml above).
export function clientBodyHtml(c, matches, via) {
  return `
    <p class="mb-3 text-sm text-gray-500">${via ? `${t('companies.via')} <a href="#agencies/${via.id}" class="text-blue-400 underline hover:text-blue-300">${escapeHtml(via.name)}</a>` : t('companies.viaDirect')}</p>
    <div class="mb-6 space-y-1 text-sm">
      <div><span class="text-gray-500">${t('companies.website')}:</span> ${c.website ? `<a href="${c.website}" target="_blank" rel="noreferrer" class="break-all text-blue-400 underline hover:text-blue-300">${c.website}</a>` : '—'}</div>
      <div><span class="text-gray-500">LinkedIn:</span> ${c.linkedin ? `<a href="${c.linkedin}" target="_blank" rel="noreferrer" class="break-all text-blue-400 underline hover:text-blue-300">${c.linkedin}</a>` : '—'}</div>
    </div>
    ${c.notes ? `<h2 class="mb-2 text-sm font-medium text-gray-400">${t('form.notes')}</h2><p class="mb-6 whitespace-pre-wrap text-sm text-gray-300">${renderNotes(c.notes)}</p>` : ''}
    <h2 class="mb-2 mt-4 text-sm font-medium text-gray-400">${t('companies.timeline', { count: matches.length })}</h2>
    <div class="space-y-2">${timelineHtml(matches)}</div>
  `
}

// Clients have no stored status (unlike agencies) — same tie-break rule,
// derived live from their own Timeline's true latest event.
export function isClientArchived(matches) {
  const latest = matches.slice().sort(byDateTimeDesc)[0]
  return latest ? isClosingEvent(latest.event) : false
}

// The names the company fields suggest: only the active agencies and clients, since one that is closed is not
// who a new event is about. A closed one can still be typed in (and a new event reactivates it).
export function activeCompanyNames(agencies, clients, events) {
  return {
    agencies: agencies.filter((a) => a.status !== 'archived').map((a) => a.name),
    clients: clients.filter((c) => !isClientArchived(events.filter((e) => e.clientId === c.id))).map((c) => c.name),
  }
}

function clientCardHtml(c, applications, agenciesMap, isOpen) {
  const matches = applications.filter((app) => app.clientId === c.id)
  const via = agenciesMap.get(c.viaAgencyId)
  const archived = isClientArchived(matches)
  return `
    <div class="capsule" data-key="client:${c.id}" data-open="${isOpen}">
      <div class="capsule-header">
        <button type="button" class="capsule-summary" aria-expanded="${isOpen}">
          <div class="flex w-full items-center gap-2">
            <span>🏢</span>
            <span class="font-medium text-gray-100">${escapeHtml(c.name)}</span>
            ${kindTagHtml('client')}
            ${via ? `<span class="text-xs text-gray-500">${t('companies.viaLower')} ${escapeHtml(via.name)}</span>` : ''}
            <span class="ml-auto rounded-full px-2 py-0.5 text-[10px] ${archived ? 'bg-gray-800 text-red-400' : 'bg-gray-800 text-emerald-400'}">${archived ? t('companies.statusArchived') : t('companies.statusActive')}</span>
          </div>
        </button>
        <button type="button" class="capsule-edit-btn client-edit-btn rounded-full bg-gray-100 px-4 py-1 text-sm font-medium text-gray-900 hover:bg-white" data-id="${c.id}">${t('common.edit')}</button>
      </div>
      <div class="capsule-body-wrap">
        <div class="capsule-body">${clientBodyHtml(c, matches, via)}</div>
      </div>
    </div>
  `
}

function renderToolbar() {
  document.getElementById('filter-active-btn').classList.toggle('active', statusFilterKey === 'active')
  document.getElementById('filter-archived-btn').classList.toggle('active', statusFilterKey === 'archived')
}

// Agencies and clients in one list, by name, each tagged with its kind.
function listHtml({ applications, agenciesMap, clientsMap }, openKey) {
  const agencies = Array.from(agenciesMap.values()).map((a) => ({ kind: 'agency', entity: a, archived: a.status === 'archived' }))
  const clients = Array.from(clientsMap.values()).map((c) => ({
    kind: 'client',
    entity: c,
    archived: isClientArchived(applications.filter((app) => app.clientId === c.id)),
  }))
  const cards = [...agencies, ...clients]
    .filter((e) => matchesStatusFilter(e.archived))
    .sort((a, b) => a.entity.name.localeCompare(b.entity.name))
    .map((e) => {
      const isOpen = `${e.kind}:${e.entity.id}` === openKey
      return e.kind === 'agency' ? agencyCardHtml(e.entity, applications, isOpen) : clientCardHtml(e.entity, applications, agenciesMap, isOpen)
    })
  return `<div class="space-y-2">${cards.join('')}</div>`
}

function wireCards(content, { applications, agenciesMap, clientsMap, onOpenEvent }) {
  wireAccordion(content)

  content.querySelectorAll('.agency-edit-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const agency = agenciesMap.get(btn.dataset.id)
      openEntityEdit('agency', btn.dataset.id, agency, undefined, agency.status === 'archived')
    })
  })
  content.querySelectorAll('.client-edit-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const client = clientsMap.get(btn.dataset.id)
      const archived = isClientArchived(applications.filter((app) => app.clientId === client.id))
      openEntityEdit('client', btn.dataset.id, client, agenciesMap.get(client.viaAgencyId)?.name, archived)
    })
  })
  content.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      e.preventDefault()
      location.hash = a.getAttribute('href').slice(1)
    })
  })
  content.querySelectorAll('.timeline-row').forEach((row) => {
    const open = () => {
      const app = applications.find((a) => a.id === row.dataset.appId)
      if (app) onOpenEvent(app)
    }
    row.addEventListener('click', (e) => {
      // A link inside the notes (e.g. a JD URL) should navigate, not open the event.
      if (e.target.closest('a')) return
      open()
    })
    row.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        open()
      }
    })
  })
}

function renderList(openKey, deps, transition = 'auto') {
  lastOpenId = openKey
  lastDeps = deps
  renderToolbar()
  const content = document.getElementById('companies-content')
  const loaded = deps.agenciesLoaded && deps.clientsLoaded

  const renderContent = () => {
    content.innerHTML = loaded ? listHtml(deps, openKey) : spinnerHtml()
    if (!loaded) return
    wireCards(content, deps)
    if (openKey) {
      const opened = content.querySelector(`.capsule[data-key="${openKey}"]`)
      if (opened) opened.scrollIntoView({ block: 'start' })
    }
  }

  if (transition === 'fade') fadeTransition(content, renderContent)
  else renderContent()
}

// Companies live entirely inline as an accordion — no separate detail page/back
// button. A deep link to a specific agency/client (from a calendar event's
// "Agency"/"Client" link, or a "Via" link) just opens the list with that card
// already expanded.
export function renderCompanies(route, deps) {
  const { openAgencyId, openClientId } = route
  const openKey = openAgencyId ? `agency:${openAgencyId}` : openClientId ? `client:${openClientId}` : null
  renderList(openKey, deps)
}

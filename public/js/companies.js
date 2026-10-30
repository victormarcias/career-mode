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

// What is typed in the search box: only the companies whose name has it (ignoring case and accents) are listed.
let searchText = ''

// Whether a company is listed under a tab.
export function inTab(company, key) {
  if (key === null) return true
  return (company.status === 'archived') === (key === 'archived')
}

const plain = (text) => (text ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()

export function matchesSearch(name, query) {
  return plain(name).includes(plain(query))
}

// How many companies are active and how many archived, whatever is typed in the search box.
export function companyCounts(companies) {
  const archived = companies.filter((c) => c.status === 'archived').length
  return { active: companies.length - archived, archived }
}

// The tag at the right of a company says its status, on the same dark capsule whatever it is. An archived one says how it was
// closed (`closedBy` in the API): the emoji of the event that closed it and a text in a color like the emoji's. Ghosted, the
// archive by hand, is no event of its own, so it has the ghost, in whitish gray.
const CLOSED_BY_LOOKS = {
  ghosted: { emoji: '👻', color: 'text-gray-300' },
  rejection: { emoji: EVENT_LABELS.rejection.emoji, color: 'text-red-400' },
  red_flag: { emoji: EVENT_LABELS.red_flag.emoji, color: 'text-orange-400' },
  on_hold: { emoji: EVENT_LABELS.on_hold.emoji, color: 'text-amber-400' },
  offer: { emoji: EVENT_LABELS.offer.emoji, color: 'text-emerald-400' },
}

export function statusTag(company) {
  if (company.status !== 'archived') return { emoji: '', text: t('companies.statusActive'), classes: 'bg-gray-800 text-emerald-400' }
  const key = company.closedBy in CLOSED_BY_LOOKS ? company.closedBy : 'ghosted'
  const { emoji, color } = CLOSED_BY_LOOKS[key]
  return { emoji, text: t(`companies.closedBy.${key}`), classes: `bg-gray-800 ${color}` }
}

// The tab a typed name belongs to: the one already selected while it lists a match, else the other when that is where
// the match is (an archived company is found from the Active tab), else the one selected. Not a filter at all (null) stays.
export function tabForSearch(companies, query, current) {
  if (current === null || !plain(query)) return current
  const found = (key) => companies.some((c) => inTab(c, key) && matchesSearch(c.name, query))
  if (found(current)) return current
  const other = current === 'active' ? 'archived' : 'active'
  return found(other) ? other : current
}

// The tab a company is opened in: the one it is in, unless nothing is selected (everything is listed).
export function tabForCompany(company, current) {
  return current === null ? null : company.status === 'archived' ? 'archived' : 'active'
}

// Filtering as the person types: the cards are drawn again, the box is not touched.
export function setSearch(text) {
  searchText = text
  if (lastDeps) {
    statusFilterKey = tabForSearch(Array.from(lastDeps.companiesMap.values()), text, statusFilterKey)
    renderList(lastOpenId, lastDeps)
  }
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
export function companyTypeTagHtml(companyType) {
  const isAgency = companyType === 'agency'
  return `<span class="rounded-full px-2 py-0.5 text-[10px] ${isAgency ? 'bg-blue-950 text-blue-300' : 'bg-violet-950 text-violet-300'}">${isAgency ? t('companies.agency') : t('companies.client')}</span>`
}

// The events a company is in: its own, and those of the clients that came through it (when it is an agency).
export function eventsOf(applications, company) {
  return applications.filter((app) => app.companyId === company.id || app.viaCompanyId === company.id)
}

const linkHtml = (url) => `<a href="${url}" target="_blank" rel="noreferrer" class="break-all text-blue-400 underline hover:text-blue-300">${url}</a>`

// Exported for follow-up.js, which reuses this exact card body inside its own expandable results list: "the same
// card as Companies", not a rebuild. `via` is the agency a client came through, when it has one.
export function companyBodyHtml(c, matches, via) {
  const recruiters = c.recruiters?.length
    ? c.recruiters.map((url) => `<a href="${url}" target="_blank" rel="noreferrer" class="block text-blue-400 underline hover:text-blue-300">${url}</a>`).join('')
    : `<p class="text-gray-500">${t('companies.noRecruiters')}</p>`
  const application = t('companies.application')
  return `
    ${c.companyType === 'client' ? `<p class="mb-3 text-sm text-gray-500">${via ? `${t('companies.via')} <a href="#companies/${via.id}" class="text-blue-400 underline hover:text-blue-300">${escapeHtml(via.name)}</a>` : t('companies.viaDirect')}</p>` : ''}
    ${c.notes ? `<p class="mb-4 whitespace-pre-wrap text-sm leading-relaxed text-gray-300">${renderNotes(c.notes)}</p>` : ''}
    <div class="mb-6 space-y-1 text-sm">
      <div><span class="text-gray-500">${t('companies.website')}:</span> ${c.website ? linkHtml(c.website) : '—'}</div>
      <div><span class="text-gray-500">LinkedIn:</span> ${c.linkedin ? linkHtml(c.linkedin) : '—'}</div>
    </div>
    <h2 class="mb-2 text-sm font-medium text-gray-400">${t('companies.recruiters')}</h2>
    <div class="mb-6 space-y-1 text-sm">${recruiters}</div>
    ${
      c.applicationLink
        ? `<a href="${applicationLinkHref(c.applicationLink)}" target="_blank" rel="noreferrer" class="mb-6 inline-block rounded-full bg-gray-100 px-4 py-2 text-sm font-medium text-gray-900 hover:bg-white">${application} →</a>`
        : `<span class="mb-6 inline-block cursor-not-allowed rounded-full bg-gray-800 px-4 py-2 text-sm font-medium text-gray-500">${application} →</span>`
    }
    <h2 class="mb-2 mt-4 text-sm font-medium text-gray-400">${t('companies.timeline', { count: matches.length })}</h2>
    <div class="space-y-2">${timelineHtml(matches)}</div>
  `
}

// The names the company fields suggest: only the active companies, since one that is closed is not who a new
// event is about. A closed one can still be typed in (and a new event reactivates it).
export function activeCompanies(companies) {
  return companies.filter((c) => c.status !== 'archived')
}

function companyCardHtml(c, applications, companiesMap, isOpen) {
  const matches = eventsOf(applications, c)
  const via = companiesMap.get(c.viaCompanyId)
  const tag = statusTag(c)
  return `
    <div class="capsule" data-key="${c.id}" data-open="${isOpen}">
      <div class="capsule-header">
        <button type="button" class="capsule-summary" aria-expanded="${isOpen}">
          <div class="flex w-full items-center gap-2">
            <span>🏢</span>
            <span class="font-medium text-gray-100">${escapeHtml(c.name)}</span>
            ${companyTypeTagHtml(c.companyType)}
            ${via ? `<span class="text-xs text-gray-500">${t('companies.viaLower')} ${escapeHtml(via.name)}</span>` : ''}
            <span class="ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium leading-none ${tag.classes}">${tag.emoji ? `<span>${tag.emoji}</span>` : ''}<span>${tag.text}</span></span>
          </div>
        </button>
        <button type="button" class="capsule-edit-btn company-edit-btn rounded-full bg-gray-100 px-4 py-1 text-sm font-medium text-gray-900 hover:bg-white" data-id="${c.id}">${t('common.edit')}</button>
      </div>
      <div class="capsule-body-wrap">
        <div class="capsule-body">${companyBodyHtml(c, matches, via)}</div>
      </div>
    </div>
  `
}

function renderToolbar(companiesMap) {
  const counts = companyCounts(Array.from(companiesMap.values()))
  const active = document.getElementById('filter-active-btn')
  const archived = document.getElementById('filter-archived-btn')
  active.textContent = t('companies.active', { count: counts.active })
  archived.textContent = t('companies.archived', { count: counts.archived })
  active.classList.toggle('active', statusFilterKey === 'active')
  archived.classList.toggle('active', statusFilterKey === 'archived')
}

// Agencies and clients in one list, by name, each tagged with its type.
function listHtml({ applications, companiesMap }, openId) {
  const cards = Array.from(companiesMap.values())
    .filter((c) => inTab(c, statusFilterKey) && matchesSearch(c.name, searchText))
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((c) => companyCardHtml(c, applications, companiesMap, c.id === openId))
  if (!cards.length) return `<p class="py-10 text-center text-sm text-gray-500">${t('companies.noResults')}</p>`
  return `<div class="space-y-2">${cards.join('')}</div>`
}

function wireCards(content, { applications, companiesMap, onOpenEvent }) {
  wireAccordion(content)

  content.querySelectorAll('.company-edit-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const company = companiesMap.get(btn.dataset.id)
      openEntityEdit(company, companiesMap.get(company.viaCompanyId)?.name, company.status === 'archived')
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

function renderList(openId, deps, transition = 'auto') {
  lastOpenId = openId
  lastDeps = deps
  renderToolbar(deps.companiesMap)
  const content = document.getElementById('companies-content')

  const renderContent = () => {
    content.innerHTML = deps.companiesLoaded ? listHtml(deps, openId) : spinnerHtml()
    if (!deps.companiesLoaded) return
    wireCards(content, deps)
    if (openId) {
      const opened = content.querySelector(`.capsule[data-key="${openId}"]`)
      if (opened) opened.scrollIntoView({ block: 'start' })
    }
  }

  if (transition === 'fade') fadeTransition(content, renderContent)
  else renderContent()
}

// Companies live entirely inline as an accordion — no separate detail page/back
// button. A deep link to a company (from a "Via" link) just opens the list with that card
// already expanded.
export function renderCompanies(route, deps) {
  if (route.openCompanyId && searchText) {  // a link to a company has to find it: the search is cleared
    searchText = ''
    document.getElementById('company-search').value = ''
  }
  const opened = deps.companiesMap.get(route.openCompanyId)  // and so is its tab: an archived company is not under Active
  if (opened) statusFilterKey = tabForCompany(opened, statusFilterKey)
  renderList(route.openCompanyId ?? null, deps)
}

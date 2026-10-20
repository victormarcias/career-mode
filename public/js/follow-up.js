import { escapeHtml, wireAccordion } from './dom-utils.js'
import { daysSince } from './dates.js'
import { t } from './i18n.js'
import { archiveCompany } from './entity-edit.js'
import { agencyBodyHtml, clientBodyHtml, isClientArchived, kindTagHtml } from './companies.js'

// A manual "no news, I'm archiving this by hand" review — the user picks a
// staleness threshold, gets back the active agencies and clients whose last
// application is at least that old, and archives whichever ones he confirms. Nothing here is reactive (no live refresh): it's a one-shot
// report fetched on demand, not a live view.

let wired = false
let currentResults = []
let lastDeps = null

// The days badge shifts from green (0 days) to red (this many days or more).
const HEAT_MAX_DAYS = 30

function heatStyle(days) {
  const hue = Math.round(120 * (1 - Math.min(days, HEAT_MAX_DAYS) / HEAT_MAX_DAYS))
  return `background-color:hsl(${hue} 55% 16%);color:hsl(${hue} 85% 68%)`
}

function sortResults(results, mode) {
  const byName = (a, b) => a.entity.name.localeCompare(b.entity.name)
  const compare = {
    name: byName,
    days: (a, b) => b.days - a.days || byName(a, b), // oldest first
    newest: (a, b) => a.days - b.days || byName(a, b),
  }[mode]
  return results.slice().sort(compare)
}

function spinnerHtml() {
  return '<div class="flex justify-center py-10"><div class="h-6 w-6 animate-spin rounded-full border-2 border-gray-700 border-t-gray-300"></div></div>'
}

// The days are counted from the day of the entity's LAST application: that is the one still waiting for an answer.
// A recruiter's message that started the conversation (a passive message) counts as an application here. With none
// of them (only interviews or notes, say) it falls back to the last event of any kind, so the company still shows up.
const APPLICATION_TYPES = ['application', 'passive_message']

export function lastApplicationDate(matches) {
  const latest = (list) => (list.length ? list.map((a) => a.date).reduce((max, d) => (d > max ? d : max)) : null)
  return latest(matches.filter((a) => APPLICATION_TYPES.includes(a.event))) ?? latest(matches)
}

export function computeStale(minDays, { agenciesMap, clientsMap, applications }) {
  const results = []

  for (const agency of agenciesMap.values()) {
    if (agency.status === 'archived') continue
    const matches = applications.filter((app) => app.agencyId === agency.id)
    const lastOn = lastApplicationDate(matches)
    if (!lastOn) continue
    const days = daysSince(lastOn)
    if (days >= minDays) results.push({ kind: 'agency', entity: agency, days, matches })
  }

  // Clients have no stored status — "active" is derived from their own
  // Timeline (same rule as the Companies tab), so one whose agency was already
  // archived can still be sitting here active.
  for (const client of clientsMap.values()) {
    const matches = applications.filter((app) => app.clientId === client.id)
    const lastOn = lastApplicationDate(matches)
    if (!lastOn || isClientArchived(matches)) continue
    const days = daysSince(lastOn)
    if (days >= minDays) {
      const via = agenciesMap.get(client.viaAgencyId)
      results.push({ kind: 'client', entity: client, days, matches, via })
    }
  }

  return results
}

function resultCardHtml({ kind, entity, days, matches, via }) {
  const isAgency = kind === 'agency'
  const body = isAgency ? agencyBodyHtml(entity, matches) : clientBodyHtml(entity, matches, via)
  return `
    <div class="capsule" data-id="${entity.id}" data-open="false">
      <div class="capsule-header">
        <label class="flex items-center pl-4">
          <input type="checkbox" class="check-item-cb h-4 w-4 rounded border-gray-700 bg-gray-800" value="${kind}:${entity.id}" />
        </label>
        <button type="button" class="capsule-summary" aria-expanded="false">
          <div class="flex w-full items-center gap-2">
            <span>🏢</span>
            <span class="font-medium text-gray-100">${escapeHtml(entity.name)}</span>
            ${kindTagHtml(kind)}
            ${via ? `<span class="text-xs text-gray-500">${t('companies.viaLower')} ${escapeHtml(via.name)}</span>` : ''}
            <span class="ml-auto rounded-full px-2 py-0.5 text-[10px]" style="${heatStyle(days)}">${t(days === 1 ? 'followUp.dayOne' : 'followUp.dayMany', { count: days })}</span>
          </div>
        </button>
      </div>
      <div class="capsule-body-wrap">
        <div class="capsule-body">${body}</div>
      </div>
    </div>
  `
}

function resultsListHtml(results) {
  if (!results.length) {
    return `<p class="py-10 text-center text-sm text-gray-500">${t('followUp.none')}</p>`
  }
  return `<div class="space-y-2">${results.map(resultCardHtml).join('')}</div>`
}

function setArchiveBtnVisible(visible) {
  document.getElementById('follow-up-archive-btn').classList.toggle('hidden', !visible)
}

function renderIdle() {
  document.getElementById('follow-up-content').innerHTML = ''
  setArchiveBtnVisible(false)
}

function renderLoading() {
  document.getElementById('follow-up-content').innerHTML = spinnerHtml()
  setArchiveBtnVisible(false)
}

function renderResults(deps) {
  const content = document.getElementById('follow-up-content')
  content.innerHTML = resultsListHtml(currentResults)
  setArchiveBtnVisible(currentResults.length > 0)
  wireAccordion(content)
  content.querySelectorAll('.timeline-row').forEach((row) => {
    const open = () => {
      const app = deps.applications.find((a) => a.id === row.dataset.appId)
      if (app) deps.onOpenEvent(app)
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

function renderSuccess(count) {
  document.getElementById('follow-up-content').innerHTML =
    `<p class="py-10 text-center text-sm text-emerald-400">${t(count === 1 ? 'followUp.archivedOne' : 'followUp.archivedMany', { count })}</p>`
  setArchiveBtnVisible(false)
}

function handleFetch(getDeps) {
  renderLoading()
  const days = Number(document.getElementById('follow-up-days').value) || 0
  lastDeps = getDeps()
  currentResults = sortResults(computeStale(days, lastDeps), document.getElementById('follow-up-sort').value)
  renderResults(lastDeps)
}

// Re-sorts what's already on screen without refetching, keeping the ticked boxes.
function handleSortChange() {
  if (!currentResults.length) return
  const content = document.getElementById('follow-up-content')
  const checked = new Set(Array.from(content.querySelectorAll('.check-item-cb:checked')).map((cb) => cb.value))
  currentResults = sortResults(currentResults, document.getElementById('follow-up-sort').value)
  renderResults(lastDeps)
  content.querySelectorAll('.check-item-cb').forEach((cb) => {
    cb.checked = checked.has(cb.value)
  })
}

async function handleArchive() {
  const content = document.getElementById('follow-up-content')
  const selected = Array.from(content.querySelectorAll('.check-item-cb:checked')).map((cb) => cb.value)
  if (!selected.length) return

  renderLoading()
  for (const value of selected) {
    const [kind, id] = value.split(':')
    await archiveCompany(kind, id, t('followUp.archiveNote'))
  }
  renderSuccess(selected.length)
}

// `getDeps` is a getter (not a plain object) because agenciesMap/clientsMap/
// applications are reassigned on every refresh from the server in main.js — this
// needs whatever is current at the moment Fetch is actually clicked.
export function initFollowUp(getDeps) {
  if (wired) return
  wired = true
  document.getElementById('follow-up-fetch-btn').addEventListener('click', () => handleFetch(getDeps))
  document.getElementById('follow-up-archive-btn').addEventListener('click', () => handleArchive())
  document.getElementById('follow-up-sort').addEventListener('change', handleSortChange)
}

export function renderFollowUp() {
  document.getElementById('follow-up-days').value = 0
  document.getElementById('follow-up-sort').value = 'days'
  currentResults = []
  renderIdle()
}

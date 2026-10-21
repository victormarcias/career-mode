import { calendar, settings } from './api.js'
import { addDays, toISODate } from './dates.js'
import { EVENT_LABELS } from './events.js'
import { companyFromNames, companyHint, companyMatches, companyNames, escapeHtml, kindConflict, kindConflictText, kindFor, setNotice } from './dom-utils.js'
import { t } from './i18n.js'

// What an event of the calendar can be logged as (the server accepts only these two).
export const SYNC_TYPES = ['hr_intro', 'tech_interview', 'culture_interview']

const STATUS_MS = 8000

// The Monday to Friday the calendar is showing, as the dates the server wants.
export function weekDates(weekStart) {
  return { start: toISODate(weekStart), end: toISODate(addDays(weekStart, 4)) }
}

// What to say when there is nothing to confirm, or after a sync.
export function repeatingNote(recurringSkipped) {
  return recurringSkipped ? ` ${t(recurringSkipped === 1 ? 'sync.repeatingOne' : 'sync.repeatingMany', { count: recurringSkipped })}` : ''
}

export function syncSummary({ created, updated }) {
  const parts = []
  if (created) parts.push(t(created === 1 ? 'sync.addedOne' : 'sync.addedMany', { count: created }))
  if (updated) parts.push(t(updated === 1 ? 'sync.movedOne' : 'sync.movedMany', { count: updated }))
  return `${parts.length ? parts.join(', ') : t('sync.nothingChanged')}.`
}

// The button works only once a calendar is set in Settings.
export function applySyncState(button, configured) {
  button.disabled = !configured
  const title = configured ? t('sync.title') : t('calendar.syncOff')
  button.title = title
  button.setAttribute('aria-label', title)
}

// ---------- The popup ----------

const SELECT_CLASS =
  'select-chevron w-44 shrink-0 appearance-none rounded-lg border border-gray-700 bg-gray-800 py-1.5 pl-3 pr-8 text-sm text-gray-100'
const KIND_CLASS =
  'select-chevron w-28 shrink-0 appearance-none rounded-lg border border-gray-700 bg-gray-800 py-1.5 pl-3 pr-8 text-sm text-gray-100'
const INPUT_CLASS = 'min-w-0 flex-1 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-100'

const typeOptions = (selected) =>
  SYNC_TYPES.map((type) => `<option value="${type}"${type === selected ? ' selected' : ''}>${EVENT_LABELS[type].emoji} ${EVENT_LABELS[type].label}</option>`).join('')

// The fields of the company of a new event: its name, its tag and, for a client, the agency it comes via.
function companyFieldsHtml(i, item) {
  const company = companyFromNames(item.agency ?? '', item.client ?? '')
  const kind = (value, label) => `<option value="${value}"${company.kind === value ? ' selected' : ''}>${t(label)}</option>`
  return `<div class="flex gap-2 pl-7">
            <input type="text" data-company="${i}" list="company-list" autocomplete="off" placeholder="${t('form.company')}" aria-label="${escapeHtml(t('sync.companyOf', { summary: item.summary }))}"
              value="${escapeHtml(company.name)}" class="${INPUT_CLASS}" />
            <select data-kind="${i}" aria-label="${escapeHtml(t('sync.kindOf', { summary: item.summary }))}" class="${KIND_CLASS}">${kind('agency', 'form.agency')}${kind('client', 'form.client')}</select>
          </div>
          <div data-via-wrap="${i}" class="pl-7${company.kind === 'client' ? '' : ' hidden'}">
            <input type="text" data-via="${i}" list="agency-list" autocomplete="off" placeholder="${t('form.via')}" aria-label="${escapeHtml(t('sync.viaOf', { summary: item.summary }))}"
              value="${escapeHtml(company.via)}" class="w-full ${INPUT_CLASS.replace('flex-1 ', '')}" />
          </div>
          <p data-hint="${i}" class="notice pl-7 text-xs text-amber-400"></p>`
}

// One row per event the sync would add (or move): a checkbox, when and what, the type to log it as and, for a new
// event, its company, with the same fields as the Update form (the company, its Agency or Client tag and, for a
// client, the agency it comes via). `item.type` is the server's suggestion ("tech" in the title picks Technical
// interview, "culture" Culture Interview), `item.agency` and `item.client` its offer.
// A name the app does not have yet is created when the event is added, so an event can be the first of its company.
export function syncRowsHtml(items) {
  return items
    .map((item, i) => {
      const moved = item.action === 'moved'
      const company = moved
        ? `<p class="pl-7 text-xs text-gray-500">${t('sync.companyStays', { company: [item.agency, item.client].filter(Boolean).map(escapeHtml).join(' → ') || t('sync.none') })}</p>`
        : companyFieldsHtml(i, item)
      return `
        <li class="space-y-2 rounded-xl border border-gray-800 bg-gray-950/40 px-3 py-2">
          <div class="flex items-center gap-3">
            <input type="checkbox" data-row="${i}" checked aria-label="${escapeHtml(t('sync.addItem', { summary: item.summary }))}"
              class="h-4 w-4 shrink-0 rounded border-gray-700 bg-gray-800" />
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm text-gray-100" title="${escapeHtml(item.notes ?? '')}">${escapeHtml(item.summary)}${moved ? `<span class="ml-2 rounded-full bg-gray-800 px-2 py-0.5 text-[11px] text-gray-400">${t('sync.movedInGoogle')}</span>` : ''}</p>
              <p class="truncate text-xs text-gray-500">${escapeHtml(item.date)} ${escapeHtml(item.time)}</p>
            </div>
            <select data-type="${i}" aria-label="${escapeHtml(t('sync.typeOf', { summary: item.summary }))}"
              class="${SELECT_CLASS}"${moved ? ` disabled title="${t('sync.alreadyLogged')}"` : ''}>${typeOptions(item.type)}</select>
          </div>
          ${company}
        </li>`
    })
    .join('')
}

export function confirmLabel(count) {
  if (!count) return t('sync.nothingSelected')
  return t(count === 1 ? 'sync.confirmOne' : 'sync.confirmMany', { count })
}

// What to send for the popup as it stands: the ticked rows, each with its type and, when it is new, its company.
// `state` is [{checked, type, agency, client}], in the order of `items`.
export function syncPayload(items, state) {
  return items.flatMap((item, i) => {
    const s = state[i]
    if (!s?.checked) return []
    if (item.action === 'moved') return [{ key: item.key, type: s.type }]
    return [{ key: item.key, type: s.type, agency: s.agency?.trim() || null, client: s.client?.trim() || null }]
  })
}

// The first ticked new event that has neither an agency nor a client, or null. Every event belongs to a company.
export function firstWithoutCompany(items, state) {
  return items.find((item, i) => state[i]?.checked && item.action === 'new' && !state[i].agency?.trim() && !state[i].client?.trim()) ?? null
}

function readState(form, items) {
  return items.map((_, i) => {
    const company = form.querySelector(`[data-company="${i}"]`)?.value ?? ''
    const kind = form.querySelector(`[data-kind="${i}"]`)?.value ?? 'agency'
    const via = form.querySelector(`[data-via="${i}"]`)?.value ?? ''
    return {
      checked: form.querySelector(`[data-row="${i}"]`).checked,
      type: form.querySelector(`[data-type="${i}"]`).value,
      company,
      kind,
      via,
      ...companyNames({ name: company, kind, via }),
    }
  })
}

// ---------- The button ----------

export async function refreshSyncButton() {
  const button = document.getElementById('sync-calendar-btn')
  try {
    const vars = await settings.env()
    applySyncState(button, Boolean(vars.find((v) => v.name === 'GOOGLE_CALENDAR_ID')?.isSet))
  } catch {
    applySyncState(button, false)
  }
}

export function initCalendarSync({ getWeekStart, getAgencies, getClients }) {
  const button = document.getElementById('sync-calendar-btn')
  const status = document.getElementById('sync-status')
  const overlay = document.getElementById('sync-overlay')
  const form = document.getElementById('sync-form')
  const list = document.getElementById('sync-list')
  const confirm = document.getElementById('sync-confirm')
  const popupError = document.getElementById('sync-error')
  let hideTimer = null
  let pending = null // {start, end, items} while the popup is open

  const say = (kind, text) => {
    status.classList.remove('text-red-400', 'text-green-400', 'text-gray-500')
    status.classList.add(kind === 'error' ? 'text-red-400' : kind === 'success' ? 'text-green-400' : 'text-gray-500')
    setNotice(status, text)
    clearTimeout(hideTimer)
    if (kind !== 'muted') hideTimer = setTimeout(() => setNotice(status, ''), STATUS_MS)
  }

  const openPopup = () => {
    button.classList.add('active') // pressed while its popup is open
    overlay.classList.remove('hidden')
    overlay.classList.add('flex')
    requestAnimationFrame(() => form.classList.add('is-open'))
  }
  const showError = (text) => {
    setNotice(popupError, text)
  }
  const closePopup = () => {
    button.classList.remove('active')
    pending = null
    showError('')
    form.classList.remove('is-open')
    setTimeout(() => {
      overlay.classList.add('hidden')
      overlay.classList.remove('flex')
    }, 150)
  }
  const refreshConfirm = () => {
    const state = readState(form, pending.items)
    const count = syncPayload(pending.items, state).length
    confirm.textContent = confirmLabel(count)
    confirm.disabled = count === 0
    pending.items.forEach((_, i) => {
      const hint = form.querySelector(`[data-hint="${i}"]`)
      if (hint) setNotice(hint, companyHint(getAgencies(), getClients(), state[i].company, state[i].kind, state[i].via))
    })
  }
  // Typing the name of a company the app knows is picking it, like in the Update form: its tag follows, and a
  // client that came through an agency fills the agency in. The agency field is only for a client.
  const showVia = (row) => {
    const kindInput = form.querySelector(`[data-kind="${row}"]`)
    form.querySelector(`[data-via-wrap="${row}"]`).classList.toggle('hidden', kindInput.value !== 'client')
  }
  const pickCompany = (row) => {
    const kindInput = form.querySelector(`[data-kind="${row}"]`)
    const viaInput = form.querySelector(`[data-via="${row}"]`)
    const name = form.querySelector(`[data-company="${row}"]`).value
    kindInput.value = kindFor(getAgencies(), getClients(), name, kindInput.value)
    const known = kindInput.value === 'client' && companyMatches(getAgencies(), getClients(), name).client
    const client = known && getClients().find((c) => c.id === known.id)
    const agency = client?.viaAgencyId && getAgencies().find((a) => a.id === client.viaAgencyId)
    if (agency && !viaInput.value.trim()) viaInput.value = agency.name
    showVia(row)
  }

  button.addEventListener('click', async () => {
    const { start, end } = weekDates(getWeekStart())
    button.disabled = true
    say('muted', t('sync.reading'))
    try {
      const plan = await calendar.preview(start, end)
      if (!plan.events.length) {
        say('success', `${t('sync.nothingNew')}${repeatingNote(plan.recurringSkipped)}`)
      } else {
        pending = { start, end, items: plan.events }
        document.getElementById('sync-subtitle').textContent =
          `${t('sync.subtitle', { start, end })}${repeatingNote(plan.recurringSkipped)}`
        list.innerHTML = syncRowsHtml(plan.events)
        refreshConfirm()
        setNotice(status, '')
        openPopup()
      }
    } catch (err) {
      say('error', err.message)
    } finally {
      await refreshSyncButton()
    }
  })

  list.addEventListener('input', (e) => {
    if (!pending) return
    if (e.target.dataset?.company !== undefined) pickCompany(e.target.dataset.company)
    refreshConfirm()
  })
  list.addEventListener('change', (e) => {
    if (!pending) return
    if (e.target.dataset?.company !== undefined) pickCompany(e.target.dataset.company)
    if (e.target.dataset?.kind !== undefined) showVia(e.target.dataset.kind)
    showError('')
    refreshConfirm()
  })
  document.getElementById('sync-cancel').addEventListener('click', closePopup)
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closePopup()
  })
  form.addEventListener('submit', async (e) => {
    e.preventDefault()
    if (!pending) return
    const { start, end, items } = pending
    const state = readState(form, items)
    const missing = firstWithoutCompany(items, state)
    if (missing) return showError(t('sync.errPickCompany', { summary: missing.summary }))
    for (const [i, item] of items.entries()) {
      const conflict = state[i].checked && item.action === 'new' && kindConflict(getAgencies(), getClients(), state[i].company, state[i].kind)
      if (conflict) return showError(kindConflictText(state[i].company, conflict))
    }
    showError('')
    confirm.disabled = true
    try {
      const result = await calendar.sync(start, end, syncPayload(items, state))
      closePopup()
      say('success', syncSummary(result))
    } catch (err) {
      confirm.disabled = false // the popup stays open, with what was picked, so nothing has to be redone
      showError(err.message)
    }
  })
  refreshSyncButton()
}

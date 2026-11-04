import { api } from './api.js'
import { EVENT_LABELS } from './events.js'
import { nextBusinessDate } from './dates.js'
import { escapeHtml, setNotice } from './dom-utils.js'
import { t } from './i18n.js'

// The Pending page: the queued links, which follow the data live, and under them a form that saves a link as a
// `pending` event. Nothing is applied to here: that is the /apply-pending skill.

// Only a link is queued: an email address alone has none of what the application needs (the recruiter, the
// role, the date), so the skill reads those from the JD Post.
export function isLink(value) {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol)
  } catch {
    return false
  }
}

// What was pasted into the box: every word is a candidate, whatever separates them (new lines, spaces). The links come
// back once each and in the order they were pasted; what is not a link comes back apart, so it can be told and kept.
export function parseLinks(text) {
  const links = []
  const invalid = []
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const list = isLink(word) ? links : invalid
    if (!list.includes(word)) list.push(word)
  }
  return { links, invalid }
}

// The queued links, oldest first.
export function queuedLinks(applications) {
  return applications
    .filter((a) => a.event === 'pending')
    .sort((a, b) => a.date.localeCompare(b.date) || (a.time ?? '').localeCompare(b.time ?? ''))
}

// One row per queued link: the link itself opens in a new tab; the pencil opens the form to edit or delete it.
export function listHtml(items) {
  if (!items.length) return `<p class="py-4 text-center text-sm text-gray-400">${t('pending.empty')}</p>`
  return items
    .map(
      (app) => `
        <div class="flex items-center gap-1 rounded-lg hover:bg-gray-800">
          <a href="${escapeHtml(app.jdUrl ?? '')}" target="_blank" rel="noreferrer" title="${escapeHtml(app.jdUrl ?? '')}"
            class="flex min-w-0 flex-1 items-center gap-3 px-3 py-2 text-sm text-gray-300 hover:text-gray-50">
            <span>${EVENT_LABELS.pending.emoji}</span>
            <span class="min-w-0 flex-1 truncate">${escapeHtml(app.jdUrl ?? '')}</span>
          </a>
          <button type="button" data-edit="${escapeHtml(app.id)}" title="${t('pending.editOrDelete')}" aria-label="${t('pending.editOrDelete')}"
            class="mr-1 shrink-0 rounded-full px-2 py-1 text-sm text-gray-500 hover:bg-gray-700 hover:text-gray-50">✏️</button>
        </div>
      `,
    )
    .join('')
}

// Redraws the queued links; main.js calls it whenever the events change while the page is on screen.
export function renderPending(applications) {
  const items = queuedLinks(applications)
  document.getElementById('pending-meta').textContent = t('pending.count', { count: items.length })
  document.getElementById('pending-list').innerHTML = listHtml(items)
  document.getElementById('pending-block').classList.toggle('hidden', !items.length)
}

// `onOpenEvent(app)` opens a queued link's form (the pencil), to edit or delete it.
export function initPending({ onOpenEvent, getApplications }) {
  const form = document.getElementById('apply-form')
  const urlInput = document.getElementById('apply-url')
  const errorEl = document.getElementById('apply-url-error')
  const feedbackEl = document.getElementById('apply-feedback')
  const submitBtn = document.getElementById('apply-form-submit')
  const list = document.getElementById('pending-list')

  function setFeedback(kind, text) {
    if (!kind) {
      feedbackEl.classList.add('hidden')
      feedbackEl.classList.remove('flex')
      return
    }
    const color = kind === 'error' ? 'text-red-400' : kind === 'success' ? 'text-green-400' : 'text-gray-400'
    feedbackEl.className = `flex items-center gap-2 text-xs ${color}`
    const spinner =
      kind === 'loading' ? '<span class="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-gray-600 border-t-gray-300"></span>' : ''
    feedbackEl.innerHTML = `${spinner}<span>${text}</span>`
  }

  urlInput.addEventListener('input', () => {
    setFeedback(null)
    setNotice(errorEl, parseLinks(urlInput.value).invalid.length ? t('pending.notALink') : '')
  })

  list.addEventListener('click', (e) => {
    const button = e.target.closest('[data-edit]')
    const app = button && getApplications().find((a) => a.id === button.dataset.edit)
    if (app) onOpenEvent(app)
  })

  // Queues one link, unless it is already queued or was applied to: which of the four it was.
  async function queueOne(link) {
    try {
      const sameLink = await api.list('events', { jdUrl: link })
      if (sameLink.length) return sameLink.some((e) => e.event === 'pending') ? 'queuedBefore' : 'applied'
      await api.create('events', { date: nextBusinessDate(), event: 'pending', jdUrl: link })
      return 'queued'
    } catch {
      return 'failed'
    }
  }

  // One link keeps its own short messages; several get a summary of what happened to them.
  function summary(results, invalidCount) {
    const count = (outcome) => results.filter((r) => r.outcome === outcome).length
    const queued = count('queued')
    const failed = count('failed')
    if (results.length === 1 && !invalidCount) {
      const text = { queued: 'pending.queued', queuedBefore: 'pending.alreadyQueued', applied: 'pending.alreadyApplied', failed: 'pending.failed' }
      return { kind: queued ? 'success' : 'error', text: t(text[results[0].outcome]) }
    }
    const parts = []
    if (queued) parts.push(t(queued === 1 ? 'pending.queuedOne' : 'pending.queuedMany', { count: queued }))
    if (count('queuedBefore')) parts.push(t('pending.skipQueued', { count: count('queuedBefore') }))
    if (count('applied')) parts.push(t('pending.skipApplied', { count: count('applied') }))
    if (invalidCount) parts.push(t('pending.skipInvalid', { count: invalidCount }))
    if (failed) parts.push(t('pending.failedMany', { count: failed }))
    return { kind: queued && !failed ? 'success' : 'error', text: parts.join(' ') }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault()
    const { links, invalid } = parseLinks(urlInput.value)
    if (!links.length) {
      setNotice(errorEl, t('pending.notALink'))
      return
    }

    submitBtn.disabled = true
    setFeedback('loading', t('pending.checking'))

    try {
      const results = []
      for (const link of links) {
        setFeedback('loading', t('pending.queuing'))
        results.push({ link, outcome: await queueOne(link) })
      }
      // What could not be queued stays in the box to be fixed or tried again; with nothing left it is emptied.
      const left = [...invalid, ...results.filter((r) => r.outcome === 'failed').map((r) => r.link)]
      if (left.length) urlInput.value = left.join('\n')
      else form.reset()
      const { kind, text } = summary(results, invalid.length)
      setFeedback(kind, text)
      urlInput.focus()
    } finally {
      submitBtn.disabled = false
    }
  })
}

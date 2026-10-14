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
    const value = urlInput.value.trim()
    setNotice(errorEl, !value || isLink(value) ? '' : t('pending.notALink'))
  })

  list.addEventListener('click', (e) => {
    const button = e.target.closest('[data-edit]')
    const app = button && getApplications().find((a) => a.id === button.dataset.edit)
    if (app) onOpenEvent(app)
  })

  form.addEventListener('submit', async (e) => {
    e.preventDefault()
    const value = urlInput.value.trim()
    if (!isLink(value)) {
      setNotice(errorEl, t('pending.notALink'))
      return
    }

    submitBtn.disabled = true
    setFeedback('loading', t('pending.checking'))

    try {
      const sameLink = await api.list('events', { jdUrl: value })
      if (sameLink.length) {
        const alreadyPending = sameLink.some((e) => e.event === 'pending')
        setFeedback('error', alreadyPending ? t('pending.alreadyQueued') : t('pending.alreadyApplied'))
        return
      }

      setFeedback('loading', t('pending.queuing'))
      await api.create('events', {
        date: nextBusinessDate(),
        event: 'pending',
        jdUrl: value,
      })
      form.reset()
      setFeedback('success', t('pending.queued'))
      urlInput.focus()
    } catch {
      setFeedback('error', t('pending.failed'))
    } finally {
      submitBtn.disabled = false
    }
  })
}

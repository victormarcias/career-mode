import { googleTasks, settings } from './api.js'
import { setNotice, setNoticeWithLink } from './dom-utils.js'
import { t } from './i18n.js'

const STATUS_MS = 8000
// The three settings that turn the button on: an OAuth client and its refresh token.
export const TASKS_SETTINGS = ['GOOGLE_TASKS_CLIENT_ID', 'GOOGLE_TASKS_CLIENT_SECRET', 'GOOGLE_TASKS_REFRESH_TOKEN']

export function tasksConfigured(vars) {
  return TASKS_SETTINGS.every((name) => vars.find((v) => v.name === name)?.isSet)
}

// What a sync did: how many links went to Pending.
export function tasksSummary({ found, queued }) {
  if (queued) return `${t(queued === 1 ? 'sync.tasksQueuedOne' : 'sync.tasksQueuedMany', { count: queued })}.`
  return `${t(found ? 'sync.tasksAllLogged' : 'sync.tasksNone')}.`
}

// The links of the open tasks go to Pending, with no popup. Used by the Calendar's icon, whose message goes in the
// Calendar's status line, and by the button of the Pending page, with a line of its own.
export function initTasksSync(buttonId = 'sync-tasks-btn', statusId = 'sync-status') {
  const button = document.getElementById(buttonId)
  const status = document.getElementById(statusId)
  let hideTimer = null

  const say = (kind, text) => {
    status.classList.remove('text-red-400', 'text-green-400', 'text-gray-500')
    status.classList.add(kind === 'error' ? 'text-red-400' : kind === 'success' ? 'text-green-400' : 'text-gray-500')
    setNotice(status, text)
    clearTimeout(hideTimer)
    if (kind !== 'muted') hideTimer = setTimeout(() => setNotice(status, ''), STATUS_MS)
  }

  button.addEventListener('click', async () => {
    button.disabled = true
    try {
      // Without its settings the button says so, and where to set them.
      const vars = await settings.env().catch(() => null)
      if (vars && !tasksConfigured(vars)) {
        say('error', '')
        return setNoticeWithLink(status, t('sync.tasksNotSet'), '#settings', t('sync.goToSettings'))
      }
      say('muted', t('sync.tasksReading'))
      const result = await googleTasks.sync()
      // The links are queued even when Google refuses to mark the tasks done: the reason is said next to it.
      say(result.completeError ? 'error' : 'success', [tasksSummary(result), result.completeError].filter(Boolean).join(' '))
    } catch (err) {
      say('error', err.message)
    } finally {
      button.disabled = false
    }
  })
}

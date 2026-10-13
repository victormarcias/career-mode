import { escapeHtml, slideTransition } from './dom-utils.js'
import { t } from './i18n.js'
import { startOfWeek, addDays, toISODate, formatWeekNumber, formatWeekRange } from './dates.js'

// Weekly job-search report (it mirrors a Google Form). Computed
// fresh from whatever's in memory every time — nothing gets saved, since it's
// meant to always reflect the current data for whichever week you're looking
// at (used once a week, right before filling out the real form). A few
// questions have no matching data in this app (how an application's channel
// was chosen) — those always report 0 and the user fills them in by hand.
const QUESTIONS = [
  'hrTalked',
  'hiddenMarket',
  'byMail',
  'byPlatform',
  'passiveInterviews',
  'hrInterviews',
  'techInterviews',
  'cultureInterviews',
  'offers',
]  // the texts are in the locale files (report.q.<key>): in Spanish they are the form's own questions

function computeAnswers(applications, start, end) {
  const inWeek = applications.filter((a) => a.date >= start && a.date <= end)
  const countEvent = (type) => inWeek.filter((a) => a.event === type).length
  // An application with no detected channel (no link, or an old entry logged
  // before applyType existed) defaults to "by platform" — the common case
  // when nothing else was specified.
  const countApplyType = (type) => inWeek.filter((a) => a.event === 'application' && (a.applyType || 'web_form') === type).length

  return {
    hrTalked: 0,
    hiddenMarket: 0,
    byMail: countApplyType('email_apply'),
    byPlatform: countApplyType('web_form'),
    // The form asks about interviews that arrived passively; what's recorded is each
    // recruiter who reached out first (a passive_message event), the closest thing.
    passiveInterviews: countEvent('passive_message'),
    hrInterviews: countEvent('hr_intro'),
    techInterviews: countEvent('tech_interview'),
    cultureInterviews: countEvent('culture_interview'),
    offers: countEvent('offer'),
  }
}

// Fills the report for the week the Calendar is showing.
function renderReport(applications, weekStart) {
  const monday = startOfWeek(weekStart)
  const sunday = addDays(monday, 6)
  const start = toISODate(monday)
  const end = toISODate(sunday)
  const answers = computeAnswers(applications, start, end)

  document.getElementById('weekly-report-meta').textContent = `${formatWeekNumber(monday)} ${formatWeekRange(monday)}`

  const allZero = Object.values(answers).every((v) => v === 0)
  const content = document.getElementById('weekly-report-content')
  content.innerHTML = allZero
    ? `<p class="py-2 text-center text-sm text-gray-400">${t('report.empty')}</p>`
    : QUESTIONS.map(
        (key) => `
          <div class="flex items-center justify-between gap-4 border-b border-gray-800 py-2.5 last:border-0">
            <p class="text-sm text-gray-300">${escapeHtml(t(`report.q.${key}`))}</p>
            <span class="min-w-[2.5rem] shrink-0 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1 text-center text-sm font-medium text-gray-100">${answers[key]}</span>
          </div>
        `,
      ).join('')
}

let open = false

// The Weekly Report button looks pressed while the report is on screen.
function setButtonState() {
  const button = document.getElementById('weekly-report-btn')
  button.classList.toggle('active', open)
  button.setAttribute('aria-pressed', String(open))
}

// The report takes the place of the week grid, sliding in the way the next week does (and back the same way).
function swap(showReport, direction) {
  const show = () => {
    document.getElementById('week-grid').classList.toggle('hidden', showReport)
    document.getElementById('weekly-report-section').classList.toggle('hidden', !showReport)
  }
  if (direction) slideTransition(document.getElementById('calendar-body'), direction, show)
  else show()
}

// `applications` is the live in-memory list main.js already keeps up to date.
// `weekStart` is the Monday of whichever week is currently shown in the
// Calendar (main.js's own `weekStart`) — navigate to any past week and this
// reports on that week.
export function generateWeeklyReport(applications, weekStart) {
  renderReport(applications, weekStart)
  open = true
  setButtonState()
  swap(true, 'left')
}

export function isWeeklyReportOpen() {
  return open
}

// Redraws the report that is on screen after the data changed, without sliding it in again.
export function refreshWeeklyReport(applications, weekStart) {
  if (open) renderReport(applications, weekStart)
}

// Brings the week grid back. Without a direction it happens at once (the Calendar is about to show another
// week or an event, and the report on screen would otherwise be left showing stale, mislabeled data); with
// one ('left' | 'right') the grid slides in.
export function hideWeeklyReport(direction = null) {
  if (!open) return
  open = false
  setButtonState()
  swap(false, direction)
}

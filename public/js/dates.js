import { t } from './i18n.js'

export function startOfWeek(date) {
  const d = new Date(date)
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + diff)
  d.setHours(0, 0, 0, 0)
  return d
}

// HH:MM of a Date in the local time zone: the time a form is opened with.
export function currentTime(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`
}

// The time a form opens with: the one the event already has, or the current one for a new event or an
// event saved without a time.
export function formTime(savedTime, now = new Date()) {
  return savedTime ?? currentTime(now)
}

export function addDays(date, n) {
  const d = new Date(date)
  d.setDate(d.getDate() + n)
  return d
}

// Monday of the current week, unless `date` falls on a weekend — the grid only
// has Mon-Fri columns, so a weekend "today" should jump to the upcoming
// business week instead of the one that already had its weekdays.
export function currentOrNextBusinessWeekStart(date) {
  const monday = startOfWeek(date)
  const day = date.getDay()
  return day === 0 || day === 6 ? addDays(monday, 7) : monday
}

// YYYY-MM-DD of a Date in the local time zone. (toISOString gives the UTC date, which from 9 pm in
// Argentina is already tomorrow: the wrong "today" for a new event, an archive or the calendar.)
export function toISODate(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

// Today's date, or Monday if today is a weekend — the grid only has Mon-Fri
// columns. Shared by the Pending page form (what date to stamp a new pending
// event with) and the Calendar (where to keep showing an unprocessed pending
// item every day until it's actually acted on).
export function nextBusinessDate() {
  const d = new Date()
  const day = d.getDay() // 0 = Sunday, 6 = Saturday
  if (day === 6) d.setDate(d.getDate() + 2)
  else if (day === 0) d.setDate(d.getDate() + 1)
  return toISODate(d)
}

// Whole days between an ISO date string (e.g. an application event's `date`)
// and today — used to show how stale a still-active process is.
export function daysSince(isoDate) {
  const then = new Date(isoDate + 'T00:00:00')
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return Math.round((now - then) / 86400000)
}

// "Mon, 12 Oct" in the language of the page, whatever the computer's language (the column heading shows it in capitals).
export function formatDayLabel(date) {
  const weekdays = t('date.weekdays').split(',')
  const months = t('date.months').split(',')
  return `${weekdays[date.getDay()]}, ${date.getDate()} ${months[date.getMonth()]}`
}

function getISOWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  const dayNum = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum)
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  return Math.ceil(((d - yearStart) / 86400000 + 1) / 7)
}

export function formatWeekNumber(monday) {
  return t('calendar.week', { n: getISOWeek(monday) })
}

function pad2(n) {
  return String(n).padStart(2, '0')
}

function formatDDMM(date) {
  return `${pad2(date.getDate())}/${pad2(date.getMonth() + 1)}`
}

// DD/MM for both ends — never breaks when the week crosses a month (or year) boundary.
export function formatWeekRange(monday) {
  const friday = addDays(monday, 4)
  return `(${formatDDMM(monday)} - ${formatDDMM(friday)})`
}

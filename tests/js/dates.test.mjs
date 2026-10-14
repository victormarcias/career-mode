// The date helpers (public/js/dates.js). Dates are built from local parts, so these hold in any time zone.
// Run with: node --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

const { addDays, currentTime, formatDayLabel, formTime, nextBusinessDate, startOfWeek, toISODate } = await import('../../public/js/dates.js')

test('toISODate is the local date, even late in the evening', () => {
  assert.equal(toISODate(new Date(2026, 9, 8, 23, 30)), '2026-10-08')  // from 9 pm at UTC-3, UTC is already the next day
  assert.equal(toISODate(new Date(2026, 9, 9, 0, 5)), '2026-10-09')
  assert.equal(toISODate(new Date(2026, 0, 1)), '2026-01-01')
  assert.equal(toISODate(new Date(2026, 11, 31, 23, 59)), '2026-12-31')
})

test('currentTime is the local HH:MM, with its zeros', () => {
  assert.equal(currentTime(new Date(2026, 9, 9, 7, 5)), '07:05')
  assert.equal(currentTime(new Date(2026, 9, 9, 15, 31, 59)), '15:31')
  assert.equal(currentTime(new Date(2026, 9, 9, 0, 0)), '00:00')
  assert.equal(currentTime(new Date(2026, 9, 9, 23, 59)), '23:59')
  assert.match(currentTime(), /^\d\d:\d\d$/)
})

test('the days of a week keep their own dates', () => {
  const monday = startOfWeek(new Date(2026, 9, 8, 22, 0)) // a Thursday night
  assert.equal(toISODate(monday), '2026-10-05')
  assert.deepEqual([0, 1, 2, 3, 4].map((n) => toISODate(addDays(monday, n))), ['2026-10-05', '2026-10-06', '2026-10-07', '2026-10-08', '2026-10-09'])
})

test('a weekend jumps to Monday for a queued link, a weekday stays', () => {
  const real = Date
  const at = (y, m, d, h) => {
    globalThis.Date = class extends real {
      constructor(...args) { super(...(args.length ? args : [y, m, d, h])) }
    }
    return nextBusinessDate()
  }
  try {
    assert.equal(at(2026, 9, 10, 22), '2026-10-12')  // Saturday night
    assert.equal(at(2026, 9, 11, 9), '2026-10-12')   // Sunday
    assert.equal(at(2026, 9, 9, 22), '2026-10-09')   // Friday night
  } finally {
    globalThis.Date = real
  }
})

test('a form keeps the time an event has, and uses the current one only when there is none', () => {
  const now = new Date(2026, 9, 9, 16, 45)
  assert.equal(formTime('09:30', now), '09:30') // an edit keeps its time
  assert.equal(formTime('00:00', now), '00:00')
  assert.equal(formTime(undefined, now), '16:45') // a new event
  assert.equal(formTime(null, now), '16:45') // an event saved without a time
  assert.match(formTime(null), /^\d\d:\d\d$/)
})

test('a day is labelled in English, MON to FRI, with the day and the month', () => {
  const monday = new Date(2026, 9, 12)
  assert.deepEqual(
    [0, 1, 2, 3, 4].map((i) => formatDayLabel(addDays(monday, i))),
    ['Mon, 12 Oct', 'Tue, 13 Oct', 'Wed, 14 Oct', 'Thu, 15 Oct', 'Fri, 16 Oct'],
  )
  assert.equal(formatDayLabel(new Date(2026, 11, 31)), 'Thu, 31 Dec')
  assert.equal(formatDayLabel(new Date(2026, 0, 4)), 'Sun, 4 Jan')
})

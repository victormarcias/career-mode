// The event colors (public/js/events.js). Run with: node --test tests/js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const { EVENT_COLOR_HIGHLIGHT, EVENT_COLORS, EVENT_LABELS, INTERVIEW_ALERT_CLASS, interviewAlertOn } = await import('../../public/js/events.js')

test('the pills of one company highlight in a single dark gray, not one color per type', () => {
  assert.equal(EVENT_COLOR_HIGHLIGHT, 'bg-gray-700 text-white')
  assert.ok(!Object.values(EVENT_COLORS).includes(EVENT_COLOR_HIGHLIGHT), 'it must differ from every pill color, or nothing would change')
  const main = readFileSync(new URL('../../public/js/main.js', import.meta.url), 'utf8')
  assert.ok(main.includes('...EVENT_COLOR_HIGHLIGHT.split'), 'the week uses it for every pill')
  assert.ok(!/colorHighlight/.test(main), 'no per-type highlight is kept on the pills')
})

test('no pill is the color of the day column it sits in, or it would disappear into it', () => {
  const main = readFileSync(new URL('../../public/js/main.js', import.meta.url), 'utf8')
  assert.ok(main.includes("'border-gray-800 bg-gray-900'"), 'the day column is bg-gray-900 (update this test if it changes)')
  for (const [type, classes] of Object.entries(EVENT_COLORS)) assert.ok(!classes.split(' ').includes('bg-gray-900'), type)
  assert.equal(EVENT_COLORS.tech_interview, 'bg-black text-green-400')
})

test('the HR intro is a strong dark green with white text', () => {
  assert.equal(EVENT_COLORS.hr_intro, 'bg-green-800 text-white')
  assert.equal(EVENT_LABELS.hr_intro.emoji, '☎️', 'the red telephone, which shows on the dark green')
})

test('an interview gets the alert from 10 minutes before until 30 minutes after it starts', () => {
  const at = (hh, mm) => new Date(2026, 10, 5, hh, mm)
  const interview = { event: 'hr_intro', date: '2026-11-05', time: '15:00' }
  assert.equal(interviewAlertOn(interview, at(14, 49)), false, '11 minutes before')
  assert.equal(interviewAlertOn(interview, at(14, 50)), true, '10 minutes before')
  assert.equal(interviewAlertOn(interview, at(15, 0)), true, 'at the time')
  assert.equal(interviewAlertOn(interview, at(15, 29)), true, '29 minutes after')
  assert.equal(interviewAlertOn(interview, at(15, 30)), false, 'over')
  for (const event of ['tech_interview', 'culture_interview']) assert.equal(interviewAlertOn({ ...interview, event }, at(15, 0)), true, event)
})

test('only interviews with a time get the alert', () => {
  const now = new Date(2026, 10, 5, 15, 0)
  assert.equal(interviewAlertOn({ event: 'application', date: '2026-11-05', time: '15:00' }, now), false)
  assert.equal(interviewAlertOn({ event: 'hr_intro', date: '2026-11-05', time: null }, now), false)
  assert.equal(interviewAlertOn({ event: 'hr_intro', date: '2026-11-04', time: '15:00' }, now), false, 'another day')
})

test('the alert border fades in and out, and stays still for reduced motion', () => {
  const css = readFileSync(new URL('../../public/style.css', import.meta.url), 'utf8')
  assert.ok(css.includes(`.event-pill.${INTERVIEW_ALERT_CLASS} {`), 'the class main.js toggles has its style')
  assert.ok(/animation: interview-alert-fade [^;]*infinite/.test(css), 'it fades in a loop')
  assert.ok(/prefers-reduced-motion: reduce\)[\s\S]*interview-alert \{ animation: none; \}/.test(css))
})

test('an application is plain white', () => {
  assert.equal(EVENT_COLORS.application, 'bg-white text-gray-950')
})

// The Weekly Report (public/js/weekly-report.js): what it counts, what it draws, and the button that opens it.
// Run with: node --import ./tests/js/setup.mjs --test tests/js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { test } from 'node:test'

// ---------- the counting, run on its own ----------

const source = readFileSync(new URL('../../public/js/weekly-report.js', import.meta.url), 'utf8')
const start = source.indexOf('function computeAnswers(')
const ctx = {}
vm.createContext(ctx)
vm.runInContext(source.slice(start, source.indexOf('\n}\n', start) + 3) + '\nthis.computeAnswers = computeAnswers', ctx)
const answers = (events) => JSON.parse(JSON.stringify(ctx.computeAnswers(events, '2026-10-05', '2026-10-11')))

const week = (event, extra = {}) => ({ event, date: '2026-10-08', ...extra })

test('passive messages in the week are what the passive-interviews question counts', () => {
  const result = answers([week('passive_message'), week('passive_message'), week('note')])
  assert.equal(result.passiveInterviews, 2)
})

test('only the days of the week count', () => {
  const result = answers([week('passive_message', { date: '2026-10-04' }), week('passive_message', { date: '2026-10-12' }), week('passive_message', { date: '2026-10-11' })])
  assert.equal(result.passiveInterviews, 1)
})

test('the other counts are untouched, and a passive message is not an HR intro or an application', () => {
  const result = answers([week('passive_message'), week('hr_intro'), week('tech_interview'), week('culture_interview'), week('offer'), week('application', { applyType: 'email_apply' })])
  assert.deepEqual(result, {
    hrTalked: 0, hiddenMarket: 0, byMail: 1, byPlatform: 0, passiveInterviews: 1,
    hrInterviews: 1, techInterviews: 1, cultureInterviews: 1, offers: 1,
  })
})

test('an application counts by mail or by platform, and one with no channel is by platform', () => {
  const result = answers([
    week('application', { applyType: 'email_apply' }), week('application', { applyType: 'web_form' }),
    week('application', { applyType: 'web_form' }), week('application'), week('application', { applyType: null }),
  ])
  assert.deepEqual([result.byMail, result.byPlatform], [1, 4])
})

test('a queued link is not an application', () => {
  assert.ok(Object.values(answers([week('pending')])).every((n) => n === 0))
})

test('with nothing in the week every answer is 0', () => {
  assert.ok(Object.values(answers([])).every((n) => n === 0))
})

// ---------- the report on a page, and the button that presses open and shut ----------

const { generateWeeklyReport, hideWeeklyReport, isWeeklyReportOpen, refreshWeeklyReport } = await import('../../public/js/weekly-report.js')

function fakePage() {
  const elements = {}
  const el = (id) =>
    (elements[id] ??= {
      textContent: '',
      innerHTML: '',
      attrs: {},
      offsetWidth: 0,
      classes: new Set(id === 'weekly-report-section' ? ['hidden'] : []),
      setAttribute(k, v) { this.attrs[k] = v },
      classList: {
        add: (...c) => c.forEach((x) => elements[id].classes.add(x)),
        remove: (...c) => c.forEach((x) => elements[id].classes.delete(x)),
        toggle: (c, on) => elements[id].classes[on ? 'add' : 'delete'](c),
      },
    })
  globalThis.document = { getElementById: el }
  return el
}
const frame = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const monday = new Date(2026, 9, 5)

test('the report lists each question with its count, for the week it is given', () => {
  const el = fakePage()
  generateWeeklyReport([week('application', { applyType: 'email_apply' }), week('hr_intro')], monday)
  const html = el('weekly-report-content').innerHTML
  assert.equal((html.match(/rounded-lg border border-gray-700/g) ?? []).length, 9)  // one box per question
  assert.match(html, /How many jobs did you apply to by email\?/)
  assert.match(el('weekly-report-meta').textContent, /Week 41/)
  hideWeeklyReport()
})

test('with nothing to report it says so instead of listing nine zeros', () => {
  const el = fakePage()
  generateWeeklyReport([], monday)
  assert.match(el('weekly-report-content').innerHTML, /No news so far\./)
  assert.doesNotMatch(el('weekly-report-content').innerHTML, /How many/)
  hideWeeklyReport()
})

test('what is queued does not make a report', () => {
  const el = fakePage()
  generateWeeklyReport([week('pending')], monday)
  assert.match(el('weekly-report-content').innerHTML, /No news so far\./)
  hideWeeklyReport()
})

test('opening the report presses the button and takes the place of the week; closing puts both back', async () => {
  const el = fakePage()
  generateWeeklyReport([], monday)
  assert.equal(isWeeklyReportOpen(), true)
  assert.ok(el('weekly-report-btn').classes.has('active'))
  assert.equal(el('weekly-report-btn').attrs['aria-pressed'], 'true')
  assert.ok(el('calendar-body').classes.has('slide-out-left'), 'the week slides out first')
  await frame(300)
  assert.ok(el('week-grid').classes.has('hidden') && !el('weekly-report-section').classes.has('hidden'))

  hideWeeklyReport()  // with no direction it is at once
  assert.equal(isWeeklyReportOpen(), false)
  assert.ok(!el('weekly-report-btn').classes.has('active'))
  assert.equal(el('weekly-report-btn').attrs['aria-pressed'], 'false')
  assert.ok(!el('week-grid').classes.has('hidden') && el('weekly-report-section').classes.has('hidden'))
})

test('closing with a direction slides the week back in', async () => {
  const el = fakePage()
  generateWeeklyReport([], monday)
  await frame(300)
  hideWeeklyReport('right')
  assert.ok(el('calendar-body').classes.has('slide-out-right'))
  await frame(300)
  assert.ok(!el('week-grid').classes.has('hidden'))
})

test('closing a report that is not open does nothing', () => {
  const el = fakePage()
  hideWeeklyReport('left')
  assert.equal(el('calendar-body').classes.size, 0)
  assert.equal(isWeeklyReportOpen(), false)
})

test('refreshing redraws an open report, and does nothing when it is closed', async () => {
  const el = fakePage()
  refreshWeeklyReport([week('offer')], monday)
  assert.equal(el('weekly-report-content').innerHTML, '')  // closed: nothing drawn

  generateWeeklyReport([], monday)
  assert.match(el('weekly-report-content').innerHTML, /No news so far/)
  refreshWeeklyReport([week('offer')], monday)
  assert.match(el('weekly-report-content').innerHTML, /How many offer letters did you receive\?/)
  hideWeeklyReport()
  await frame(300)
})

// ---------- the four buttons of the Calendar ----------

test('the four buttons of the Calendar share one look, and the CSS gives the pressed one its own', () => {
  const css = readFileSync(new URL('../../public/style.css', import.meta.url), 'utf8')
  const html = readFileSync(new URL('../../public/index.html', import.meta.url), 'utf8')
  assert.match(css, /\.state-pill:hover:not\(:disabled\)[^{]*\{[^}]*background-color: #1f2937/)
  assert.match(css, /\.state-pill\.active\s*\{[^}]*background-color: #1f2937/)
  for (const id of ['new-application-btn', 'new-event-btn', 'sync-calendar-btn', 'weekly-report-btn']) {
    const button = html.match(new RegExp(`<button id="${id}"[^>]*>`))[0]
    assert.match(button, /class="state-pill /, id)
    assert.doesNotMatch(button, /bg-gray-|text-gray-|hover:bg-|border-gray-/, `${id}: no Tailwind color left to fight the state colors`)
  }
})

test('each of the four is on while its own form, popup or section is open', () => {
  const read = (file) => readFileSync(new URL(`../../public/js/${file}`, import.meta.url), 'utf8')
  assert.match(read('application-form.js'), /openButton\.classList\.add\('active'\)[\s\S]*openButton\.classList\.remove\('active'\)/)
  assert.match(read('main.js'), /new-event-btn'\)\.classList\.toggle\('active', !app\)/) // not while editing an event
  assert.match(read('main.js'), /new-event-btn'\)\.classList\.remove\('active'\)/)
  assert.match(read('calendar-sync.js'), /button\.classList\.add\('active'\)[\s\S]*button\.classList\.remove\('active'\)/)
})

// The Pending page (public/js/pending.js): which links are queued, how they are drawn, and the form that queues one.
// Run with: node --import ./tests/js/setup.mjs --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

const calls = []
let responder = () => ({ status: 200, body: [] })
globalThis.fetch = async (url, options = {}) => {
  calls.push({ url, method: options.method ?? 'GET', body: options.body ? JSON.parse(options.body) : undefined })
  const { status, body } = responder(url, options)
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}

const { isLink, initPending, listHtml, parseLinks, queuedLinks, renderPending } = await import('../../public/js/pending.js')
const { toISODate } = await import('../../public/js/dates.js')

const queued = (id, jdUrl, date = '2026-10-08', time = null) => ({ id, event: 'pending', jdUrl, date, time })
const note = { id: 'n', event: 'note', date: '2026-10-01', jdUrl: null }

test('only a web link can be queued: an email address, text or another kind of address cannot', () => {
  for (const ok of ['https://jobs.example/post/1', 'http://jobs.example/p', 'https://www.linkedin.com/posts/x?utm_source=share']) assert.equal(isLink(ok), true, ok)
  for (const no of ['recruiter@acme.com', 'mailto:recruiter@acme.com', 'jobs.example/post/1', 'javascript:alert(1)', 'ftp://x.example/a', 'send me your CV', '']) {
    assert.equal(isLink(no), false, no)
  }
})

test('the queue is the pending events, oldest first, whatever week they were queued in', () => {
  const list = queuedLinks([
    queued('c', 'https://c.example/job', '2026-10-09', '09:00'),
    note,
    queued('a', 'https://a.example/job', '2026-09-01'),
    queued('b', 'https://b.example/job', '2026-10-09', '08:00'),
  ])
  assert.deepEqual(list.map((a) => a.id), ['a', 'b', 'c'])
  assert.deepEqual(queuedLinks([note, { ...note, event: 'application' }]), [])
})

test('each queued link opens in a new tab with its own address, and has a pencil to edit or delete it', () => {
  const html = listHtml([queued('x1', 'https://www.example.com/jobs/12345/apply')])
  assert.match(html, /href="https:\/\/www\.example\.com\/jobs\/12345\/apply" target="_blank" rel="noreferrer"/)
  assert.match(html, /data-edit="x1"/)
  assert.match(html, /⏳/)
  assert.match(html, /title="Edit or delete"/)
})

test('with nothing queued the list says so, and what comes from the link is escaped', () => {
  assert.match(listHtml([]), /Nothing queued\./)
  const html = listHtml([queued('"><script>', '"><script>alert(1)</script>')])
  assert.doesNotMatch(html, /<script>/)
})

// ---------- on a page ----------

function fakeElement() {
  const handlers = {}
  const el = {
    value: '', textContent: '', innerHTML: '', className: '', disabled: false, focused: 0, resets: 0,
    classes: new Set(),
    classList: {
      add: (...c) => c.forEach((x) => el.classes.add(x)),
      remove: (...c) => c.forEach((x) => el.classes.delete(x)),
      toggle: (name, on) => (on ? el.classes.add(name) : el.classes.delete(name)),
    },
    addEventListener: (type, fn) => (handlers[type] = fn),
    fire: (type, event = {}) => handlers[type]({ preventDefault() {}, ...event }),
    focus() { el.focused += 1 },
    reset() { el.resets += 1; el.value = '' },
  }
  return el
}

function page() {
  const elements = {}
  globalThis.document = { getElementById: (id) => (elements[id] ??= fakeElement()) }
  calls.length = 0
  responder = () => ({ status: 200, body: [] })
  return (id) => globalThis.document.getElementById(id)
}

test('the page shows how many are queued and the list, oldest first', () => {
  const el = page()
  renderPending([queued('b', 'https://b.example/x', '2026-10-09'), queued('a', 'https://a.example/x', '2026-10-01'), note])
  assert.equal(el('pending-meta').textContent, '2 queued')
  assert.ok(el('pending-list').innerHTML.indexOf('a.example') < el('pending-list').innerHTML.indexOf('b.example'))
  assert.ok(!el('pending-block').classes.has('hidden'))
})

test('the list under the Calendar is hidden while nothing is queued', () => {
  const el = page()
  renderPending([note])
  assert.ok(el('pending-block').classes.has('hidden'))
})

test('typing something that is not a link warns at once, and clears when it is one or the box is empty', () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = 'recruiter@acme.com'
  el('apply-url').fire('input')
  assert.match(el('apply-url-error').textContent, /Enter the JD Post link/)
  assert.ok(el('apply-url-error').classes.has('is-open'))
  el('apply-url').value = 'https://jobs.example/p'
  el('apply-url').fire('input')
  assert.ok(!el('apply-url-error').classes.has('is-open'))
})

test('a link is queued as a pending event, for the next business day, with nothing else', async () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = '  https://jobs.example/post/7  '
  await el('apply-form').fire('submit')
  assert.deepEqual(calls.map((c) => [c.method, c.url]), [['GET', '/api/events?jdUrl=https%3A%2F%2Fjobs.example%2Fpost%2F7'], ['POST', '/api/events']])
  const { body } = calls[1]
  assert.deepEqual(body, { date: body.date, event: 'pending', jdUrl: 'https://jobs.example/post/7' })
  assert.match(body.date, /^\d{4}-\d\d-\d\d$/)
  assert.ok(new Date(`${body.date}T12:00:00`).getDay() % 6 !== 0, 'never a weekend')
  assert.ok(body.date >= toISODate(new Date()))
  assert.equal(el('apply-url').resets, 0)
  assert.equal(el('apply-form').resets, 1)
  assert.match(el('apply-feedback').innerHTML, /Queued\./)
  assert.equal(el('apply-form-submit').disabled, false)
})

test('an email address is refused and nothing is asked of the server', async () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = 'recruiter@acme.com'
  await el('apply-form').fire('submit')
  assert.deepEqual(calls, [])
  assert.match(el('apply-url-error').textContent, /Enter the JD Post link/)
})

test('a link that is already queued, or already applied to, is not queued again', async () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = 'https://jobs.example/post/7'
  responder = () => ({ status: 200, body: [queued('q', 'https://jobs.example/post/7')] })
  await el('apply-form').fire('submit')
  assert.match(el('apply-feedback').innerHTML, /already queued/)
  responder = () => ({ status: 200, body: [{ id: 'a', event: 'application', jdUrl: 'https://jobs.example/post/7' }] })
  await el('apply-form').fire('submit')
  assert.match(el('apply-feedback').innerHTML, /already applied/)
  assert.deepEqual(calls.filter((c) => c.method === 'POST'), [])
})

test('when the server fails the form says so and can be used again', async () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = 'https://jobs.example/post/7'
  responder = (url, options) => (options.method === 'POST' ? { status: 500, body: null } : { status: 200, body: [] })
  await el('apply-form').fire('submit')
  assert.match(el('apply-feedback').innerHTML, /Could not queue it/)
  assert.equal(el('apply-form-submit').disabled, false)
  assert.equal(el('apply-form').resets, 0, 'what was typed is kept')
})

test('the pencil of a queued link opens its form', () => {
  const el = page()
  const app = queued('x1', 'https://jobs.example/p')
  const opened = []
  initPending({ onOpenEvent: (a) => opened.push(a), getApplications: () => [app] })
  el('pending-list').fire('click', { target: { closest: () => ({ dataset: { edit: 'x1' } }) } })
  el('pending-list').fire('click', { target: { closest: () => null } })
  el('pending-list').fire('click', { target: { closest: () => ({ dataset: { edit: 'gone' } }) } })
  assert.deepEqual(opened, [app])
})

// ---------- several links at once ----------

test('what is pasted is split by lines or spaces: links once each in order, and what is not a link apart', () => {
  const text = '  https://a.example/1\r\nrecruiter@acme.com\n\nhttps://b.example/2 https://a.example/1\n  not a link  \n'
  assert.deepEqual(parseLinks(text), {
    links: ['https://a.example/1', 'https://b.example/2'],
    invalid: ['recruiter@acme.com', 'not', 'a', 'link'],
  })
  assert.deepEqual(parseLinks(''), { links: [], invalid: [] })
  assert.deepEqual(parseLinks(' \n '), { links: [], invalid: [] })
})

test('typing several lines warns if any of them is not a link', () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = 'https://a.example/1\nrecruiter@acme.com'
  el('apply-url').fire('input')
  assert.ok(el('apply-url-error').classes.has('is-open'))
  el('apply-url').value = 'https://a.example/1\nhttps://b.example/2'
  el('apply-url').fire('input')
  assert.ok(!el('apply-url-error').classes.has('is-open'))
})

const posted = () => calls.filter((c) => c.method === 'POST').map((c) => c.body.jdUrl)

test('several links are each checked and queued, in the order they were pasted', async () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = 'https://a.example/1\nhttps://b.example/2\nhttps://c.example/3'
  await el('apply-form').fire('submit')
  assert.deepEqual(posted(), ['https://a.example/1', 'https://b.example/2', 'https://c.example/3'])
  assert.equal(calls.filter((c) => c.method === 'GET').length, 3)
  assert.match(el('apply-feedback').innerHTML, /Queued 3 links\./)
  assert.equal(el('apply-form').resets, 1)
  assert.equal(el('apply-form-submit').disabled, false)
})

test('the ones already queued or applied to are skipped, and a line that is not a link stays in the box', async () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = 'https://new.example/1\nhttps://queued.example/2\nhttps://applied.example/3\nrecruiter@acme.com'
  responder = (url, options) => {
    if (options.method === 'POST') return { status: 201, body: {} }
    if (url.includes(encodeURIComponent('https://queued.example/2'))) return { status: 200, body: [queued('q', 'https://queued.example/2')] }
    if (url.includes(encodeURIComponent('https://applied.example/3'))) return { status: 200, body: [{ id: 'a', event: 'application' }] }
    return { status: 200, body: [] }
  }
  await el('apply-form').fire('submit')
  assert.deepEqual(posted(), ['https://new.example/1'])
  const text = el('apply-feedback').innerHTML
  assert.match(text, /Queued 1 link\./)
  assert.match(text, /Already queued: 1\./)
  assert.match(text, /Already applied: 1\./)
  assert.match(text, /Not links: 1\./)
  assert.equal(el('apply-url').value, 'recruiter@acme.com')
  assert.equal(el('apply-form').resets, 0)
})

test('when one fails the others are still queued, and the failed one stays in the box to try again', async () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = 'https://a.example/1\nhttps://b.example/2\nhttps://c.example/3'
  responder = (url, options) => ({ status: options.method === 'POST' && options.body.includes('b.example') ? 500 : 200, body: options.method === 'POST' ? {} : [] })
  await el('apply-form').fire('submit')
  assert.deepEqual(posted(), ['https://a.example/1', 'https://b.example/2', 'https://c.example/3'])
  assert.match(el('apply-feedback').innerHTML, /Queued 2 links\./)
  assert.match(el('apply-feedback').innerHTML, /Could not queue 1/)
  assert.equal(el('apply-url').value, 'https://b.example/2')
  assert.equal(el('apply-form-submit').disabled, false)
})

test('only text that is not a link queues nothing and asks nothing of the server', async () => {
  const el = page()
  initPending({ onOpenEvent() {}, getApplications: () => [] })
  el('apply-url').value = 'recruiter@acme.com\n   \nsend me your CV'
  await el('apply-form').fire('submit')
  assert.deepEqual(calls, [])
  assert.match(el('apply-url-error').textContent, /Enter the JD Post link/)
})

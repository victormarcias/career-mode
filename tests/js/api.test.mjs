// The front end's data layer (public/js/api.js), with fetch and EventSource faked.
// Run with: node --test tests/js
import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'

const calls = []
let responder = () => ({ status: 200, body: [] })
const sources = []

globalThis.fetch = async (url, options = {}) => {
  calls.push({ url, method: options.method ?? 'GET', body: options.body ? JSON.parse(options.body) : undefined })
  const { status, body } = responder(url, options)
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}
globalThis.EventSource = class {
  constructor(url) {
    this.url = url
    sources.push(this)
  }
}

const { api, subscribe } = await import('../../public/js/api.js')

beforeEach(() => {
  calls.length = 0
  responder = () => ({ status: 200, body: [] })
})

test('reads build the URL and skip filters that are not set', async () => {
  await api.list('events', { jdUrl: 'https://x.test/a b', agencyId: undefined, clientId: null })
  assert.equal(calls[0].url, '/api/events?jdUrl=https%3A%2F%2Fx.test%2Fa+b')
  await api.list('agencies')
  assert.equal(calls[1].url, '/api/agencies')
})

test('writes send JSON, encode the id, and 204 comes back as null', async () => {
  responder = () => ({ status: 204 })
  assert.equal(await api.remove('events', 'a/b c'), null)
  assert.equal(calls[0].url, '/api/events/a%2Fb%20c')
  assert.equal(calls[0].method, 'DELETE')

  responder = () => ({ status: 201, body: { id: 'x' } })
  assert.deepEqual(await api.create('agencies', { name: 'Acme' }), { id: 'x' })
  assert.deepEqual(calls.find((c) => c.method === 'POST').body, { name: 'Acme' })
})

test('a refusal becomes a readable message', async () => {
  responder = () => ({ status: 409, body: { detail: 'This agency still has 3 events. Delete or move them first.' } })
  await assert.rejects(api.remove('agencies', 'acme'), { message: 'This agency still has 3 events. Delete or move them first.' })
})

test('a field that did not validate names the field and drops the "Value error" prefix', async () => {
  responder = () => ({
    status: 422,
    body: { detail: [{ loc: ['body', 'time'], msg: 'Value error, must look like 15:30' }, { loc: ['body'], msg: 'Value error, A passive message needs an agency' }] },
  })
  await assert.rejects(api.create('events', {}), { message: 'time: must look like 15:30; A passive message needs an agency' })
})

test('an unexpected answer still says something useful', async () => {
  responder = () => ({ status: 500, body: null })
  await assert.rejects(api.list('events'), { message: 'The server answered 500.' })
})

test('a server that is down says how to start it', async () => {
  const real = globalThis.fetch
  globalThis.fetch = async () => {
    throw new TypeError('Failed to fetch')
  }
  await assert.rejects(api.list('events'), { message: /Is it running\? \(\.\/run-local\.sh\)/ })
  globalThis.fetch = real
})

test('subscribers get the list now, and again after every write and every "changed" from the server', async () => {
  const seen = []
  responder = (url) => ({ status: 200, body: url === '/api/agencies' ? [{ id: 'acme' }] : [] })
  await subscribe('agencies', (rows) => seen.push(rows.length))
  assert.deepEqual(seen, [1])
  assert.equal(sources.length, 1)
  assert.equal(sources[0].url, '/api/stream')

  await api.create('agencies', { name: 'Zeta' }) // the write refreshes before it resolves, so the screen is already current
  assert.equal(seen.length, 2)

  sources[0].onmessage() // another tab, a skill or the CLI changed something
  await new Promise((resolve) => setTimeout(resolve, 10))
  assert.equal(seen.length, 3)

  sources[0].onopen() // the stream reconnected after the server restarted
  await new Promise((resolve) => setTimeout(resolve, 10))
  assert.equal(seen.length, 4)
})

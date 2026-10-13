// Everything the app says to the server goes through here: one small client for
// the JSON API (documented at /docs), and a live feed that keeps the lists fresh.

import { t } from './i18n.js'

const COLLECTIONS = ['events', 'agencies', 'clients']

// The server answers errors as {"detail": "message"} (a refusal) or {"detail": [...]}
// (a field that didn't validate). Either way, turn it into one sentence for the UI.
function errorMessage(data, status) {
  const detail = data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d) => {
        const field = (d.loc ?? []).filter((p) => p !== 'body').join('.')
        const message = String(d.msg ?? '').replace(/^Value error, /, '')
        return field ? `${field}: ${message}` : message
      })
      .join('; ')
  }
  return t('profile.errServer', { status })
}

async function request(method, path, body) {
  let response
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new Error(t('api.unreachable'))
  }
  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(errorMessage(data, response.status))
  return data
}

function query(filters = {}) {
  const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v !== undefined && v !== null))
  return params.size ? `?${params}` : ''
}

// ---------- Live lists ----------

const subscribers = new Map(COLLECTIONS.map((name) => [name, new Set()]))
let stream = null

async function refresh(collection) {
  const callbacks = subscribers.get(collection)
  if (!callbacks.size) return
  const rows = await request('GET', `/api/${collection}`)
  callbacks.forEach((callback) => callback(rows))
}

const refreshAll = () => Promise.all(COLLECTIONS.map(refresh))

function openStream() {
  if (stream) return
  // The server says "changed" whenever the data does, whoever changed it (another
  // tab, a skill, the command line); EventSource also reconnects by itself.
  stream = new EventSource('/api/stream')
  stream.onopen = () => refreshAll().catch(() => {})
  stream.onmessage = () => refreshAll().catch(() => {})
}

// Calls `callback(rows)` now and again every time the collection changes.
export function subscribe(collection, callback) {
  subscribers.get(collection).add(callback)
  openStream()
  return refresh(collection).catch(() => {}) // a failure is retried when the stream (re)connects
}

// ---------- Reads and writes ----------

// A write returns once the lists have refreshed, so the screen already shows it.
async function write(method, path, body) {
  const result = await request(method, path, body)
  await refreshAll().catch(() => {})
  return result
}

// A file as the body of a PUT (the profile photo), answered like any other request.
async function upload(path, file) {
  let response
  try {
    response = await fetch(path, { method: 'PUT', headers: { 'Content-Type': file.type || 'application/octet-stream' }, body: file })
  } catch {
    throw new Error(t('api.unreachable'))
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(errorMessage(data, response.status))
  return data
}

// The local settings (environment variables kept in .env).
export const settings = {
  env: () => request('GET', '/api/settings/env'),
  saveEnv: (values) => request('PUT', '/api/settings/env', { values }),
  // The full value of one secret: only fetched when its eye icon is clicked.
  reveal: (name) => request('GET', `/api/settings/env/${encodeURIComponent(name)}/value`),
  // The profile photo kept in profile/: its info (null when there is none), and the changes to it.
  photo: () => request('GET', '/api/settings/photo'),
  uploadPhoto: (file) => upload('/api/settings/photo', file),
  removePhoto: () => request('DELETE', '/api/settings/photo'),
}

// Google Calendar (the calendar is the GOOGLE_CALENDAR_ID setting): `preview` lists what a sync of a date range would
// add and changes nothing; `sync` logs only the events it is given, as {key, type}.
export const calendar = {
  preview: (start, end) => request('POST', '/api/calendar/preview', { start, end }),
  sync: (start, end, events) => write('POST', '/api/calendar/sync', { start, end, events }),
}

export const api = {
  list: (collection, filters) => request('GET', `/api/${collection}${query(filters)}`),
  get: (collection, id) => request('GET', `/api/${collection}/${encodeURIComponent(id)}`),
  create: (collection, data) => write('POST', `/api/${collection}`, data),
  patch: (collection, id, data) => write('PATCH', `/api/${collection}/${encodeURIComponent(id)}`, data),
  replace: (collection, id, data) => write('PUT', `/api/${collection}/${encodeURIComponent(id)}`, data),
  remove: (collection, id) => write('DELETE', `/api/${collection}/${encodeURIComponent(id)}`),
}

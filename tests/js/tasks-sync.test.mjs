import assert from 'node:assert/strict'
import test from 'node:test'
import './setup.mjs'

const { tasksConfigured, tasksSummary } = await import('../../public/js/tasks-sync.js')

const NAMES = ['GOOGLE_TASKS_CLIENT_ID', 'GOOGLE_TASKS_CLIENT_SECRET', 'GOOGLE_TASKS_REFRESH_TOKEN']
const vars = (...set) => NAMES.map((name) => ({ name, isSet: set.includes(name) }))

test('Google Tasks is configured only with its three settings', () => {
  assert.equal(tasksConfigured(vars()), false)
  assert.equal(tasksConfigured(vars(NAMES[0], NAMES[1])), false)
  assert.equal(tasksConfigured(vars(...NAMES)), true)
})

test('the message says how many links went to Pending', () => {
  assert.equal(tasksSummary({ found: 0, queued: 0, existing: 0 }), 'No links in Google Tasks.')
  assert.equal(tasksSummary({ found: 2, queued: 0, existing: 2 }), 'Every link of Google Tasks is already logged.')
  assert.equal(tasksSummary({ found: 2, queued: 1, existing: 1 }), '1 link from Google Tasks queued in Pending.')
  assert.equal(tasksSummary({ found: 3, queued: 3, existing: 0 }), '3 links from Google Tasks queued in Pending.')
})

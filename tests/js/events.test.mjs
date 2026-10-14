// The event colors (public/js/events.js). Run with: node --test tests/js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const { EVENT_COLOR_HIGHLIGHT, EVENT_COLORS } = await import('../../public/js/events.js')

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

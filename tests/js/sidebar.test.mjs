// The sidebar collapses to its icons when the window is too narrow for the content, or when the toggle says so (js/sidebar.js).
// Run with: node --import ./tests/js/setup.mjs --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

const { AUTO_COLLAPSE_BELOW, isCollapsed } = await import('../../public/js/sidebar.js')

test('with no choice made, the window decides: collapsed only while the content does not fit', () => {
  assert.equal(isCollapsed(null, AUTO_COLLAPSE_BELOW - 1), true)
  assert.equal(isCollapsed(null, AUTO_COLLAPSE_BELOW), false)
  assert.equal(isCollapsed(null, 1920), false)
  assert.equal(isCollapsed(null, 800), true)
})

test('what the person picked with the toggle wins over the window', () => {
  assert.equal(isCollapsed(true, 1920), true)
  assert.equal(isCollapsed(false, 800), false)
})

test('the Calendar fits once the sidebar is full at the point the window stops collapsing it', () => {
  const header = 904  // the Calendar header at its natural width (measured), plus its 32 px sides and the 224 px sidebar
  assert.ok(AUTO_COLLAPSE_BELOW >= header + 64 + 224)
})

// The one rule for what the page opens: a web address is a link (with https:// added when typed without it),
// anything else (a name, an email, another scheme) is text. Every card, note and form field goes through it.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { linkHref, linkHtml, renderNotes } from '../../public/js/dom-utils.js'

test('a web address is a link, typed with or without https://', () => {
  assert.equal(linkHref('https://jobs.example/123'), 'https://jobs.example/123')
  assert.equal(linkHref('http://jobs.example'), 'http://jobs.example')
  assert.equal(linkHref(' linkedin.com/in/ana-example '), 'https://linkedin.com/in/ana-example')
  assert.equal(linkHref('acme.example'), 'https://acme.example')
})

test('a name, an email or another scheme is not a link', () => {
  for (const value of ['Ana Example', 'ana@example.com', 'javascript:alert(1)', 'mailto:ana@example.com', 'https://a.example/x y', '', null]) {
    assert.equal(linkHref(value), null, String(value))
  }
})

test('linkHtml opens a link in a new tab and shows anything else as text', () => {
  assert.match(linkHtml('acme.example'), /^<a href="https:\/\/acme\.example" target="_blank" rel="noopener noreferrer"/)
  assert.equal(linkHtml('Ana <b>Example</b>'), 'Ana &lt;b&gt;Example&lt;/b&gt;')
})

test('notes turn their links clickable, and only real links', () => {
  const html = renderNotes('See https://jobs.example/1. And [the post](https://post.example/2), not [this](javascript:alert(1)).<br>Done')
  assert.match(html, /<a href="https:\/\/jobs\.example\/1"[^>]*>https:\/\/jobs\.example\/1<\/a>\./)
  assert.match(html, /<a href="https:\/\/post\.example\/2"[^>]*>the post<\/a>/)
  assert.doesNotMatch(html, /href="javascript/)
  assert.match(html, /<br>Done$/)
  assert.equal(renderNotes('<script>x</script>'), '&lt;script&gt;x&lt;/script&gt;')
})

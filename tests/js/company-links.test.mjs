// The links a company card shows (website, LinkedIn, recruiters, application) are escaped and only open
// http(s) or mailto (safeHref, public/js/dom-utils.js; companyBodyHtml, public/js/companies.js).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import './setup.mjs'

const { safeHref, escapeHtml } = await import('../../public/js/dom-utils.js')
const { companyBodyHtml } = await import('../../public/js/companies.js')

test('safeHref keeps http(s) and mailto links as they are', () => {
  assert.equal(safeHref('https://acme.example/jobs?a=1&b=2'), 'https://acme.example/jobs?a=1&amp;b=2')
  assert.equal(safeHref('http://acme.example'), 'http://acme.example')
  assert.equal(safeHref('mailto:jobs@acme.example'), 'mailto:jobs@acme.example')
})

test('safeHref opens a link typed with no https:// as https, and a bare email as mailto', () => {
  assert.equal(safeHref('acme.example'), 'https://acme.example')
  assert.equal(safeHref('  www.acme.example/careers '), 'https://www.acme.example/careers')
  assert.equal(safeHref('linkedin.example/company/acme'), 'https://linkedin.example/company/acme')
  assert.equal(safeHref('acme.example:8080/jobs'), 'https://acme.example:8080/jobs')
  assert.equal(safeHref('jobs@acme.example'), 'mailto:jobs@acme.example')
  assert.equal(safeHref('x.example/@acme'), 'https://x.example/@acme')
  assert.equal(safeHref(''), '#')
})

test('safeHref turns any other scheme into #, however it is written', () => {
  for (const url of ['javascript:alert(1)', ' JavaScript:alert(1)', 'java\tscript:alert(1)', 'data:text/html,x', 'vbscript:x']) {
    assert.equal(safeHref(url), '#', url)
  }
})

test('escapeHtml escapes quotes, so an attribute cannot be closed', () => {
  assert.equal(escapeHtml(`"' <b>&`), '&quot;&#39; &lt;b&gt;&amp;')
})

test('a company card cannot be broken out of through its links', () => {
  const evil = 'https://acme.example/" onmouseover="alert(1)'
  const html = companyBodyHtml(
    { id: 'acme', name: 'Acme', companyType: 'agency', website: evil, linkedin: 'javascript:alert(1)', recruiters: [evil], applicationLink: 'javascript:alert(1)' },
    [],
  )
  assert.ok(!html.includes('" onmouseover="'))
  assert.ok(!html.includes('href="javascript:'))
})

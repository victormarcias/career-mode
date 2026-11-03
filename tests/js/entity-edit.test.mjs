import { test } from 'node:test'
import assert from 'node:assert/strict'
import { archivableCompany } from '../../public/js/entity-edit.js'

const companies = new Map([
  ['acme', { id: 'acme', name: 'Acme Labs', status: 'active' }],
  ['old', { id: 'old', name: 'Old Corp', status: 'archived' }],
])

test("an event's active company can be archived from its form", () => {
  assert.equal(archivableCompany({ event: 'note', companyId: 'acme' }, companies)?.name, 'Acme Labs')
  assert.equal(archivableCompany({ event: 'application', companyId: 'acme' }, companies)?.id, 'acme')
})

test('nothing to archive: a new event, a queued link, an archive, no company or one already archived', () => {
  assert.equal(archivableCompany(null, companies), null)
  assert.equal(archivableCompany({ event: 'pending', companyId: null }, companies), null)
  assert.equal(archivableCompany({ event: 'archive', companyId: 'acme' }, companies), null)
  assert.equal(archivableCompany({ event: 'note', companyId: 'missing' }, companies), null)
  assert.equal(archivableCompany({ event: 'note', companyId: 'old' }, companies), null)
})

test('a website or LinkedIn field takes a link typed with no https:// (a text field, not type="url")', async () => {
  const { fieldHtml } = await import('../../public/js/entity-edit.js')
  const html = fieldHtml({ key: 'website', label: 'companies.website', type: 'url' }, 'acme.example')
  assert.ok(html.includes('type="text" inputmode="url"'))
  assert.ok(!html.includes('type="url"'))
})

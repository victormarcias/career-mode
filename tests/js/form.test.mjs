// The "+ Update" form (public/js/main.js), run with a fake page and a fake API.
// Run with: node --test tests/js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { test } from 'node:test'

// handleFormSubmit uses it, and main.js imports it from here.
const { buildNotes, parseRecruiters } = await import('../../public/js/application-form.js')
const { EVENT_LABELS, EVENT_TYPES } = await import('../../public/js/events.js')
const { t } = await import('../../public/js/i18n.js')
const { detectApplyType } = await import('../../public/js/outreach.js')  // the real one: a bare email is email, other links are web

const mainSource = readFileSync(new URL('../../public/js/main.js', import.meta.url), 'utf8')
const dom = readFileSync(new URL('../../public/js/dom-utils.js', import.meta.url), 'utf8')
  .replace(/^import .*$/gm, '')
  .replace(/^export /gm, '')
  .replace(/^const LINK_PATTERN/m, 'var LINK_PATTERN')

// Pulls one top-level function out of main.js, so the real code is what runs.
function extract(name, async = false) {
  const start = mainSource.indexOf(`${async ? 'async ' : ''}function ${name}(`)
  assert.ok(start >= 0, `${name} not found in main.js`)
  return mainSource.slice(start, mainSource.indexOf('\n}\n', start) + 3)
}

function page({ agencies = [], clients = [], fields = {}, editing = null, typeDriven = false, company = '', pending = false } = {}) {
  const calls = []
  const values = { 'f-date': '2026-10-08', 'f-time': '', 'f-event': 'note', 'f-company': '', 'f-kind': 'agency', 'f-via': '', 'f-notes': '', 'f-jd': '', 'f-apply-type': '', 'f-recruiter': '', ...fields }
  const elements = {}
  const el = (id) =>
    (elements[id] ??= {
      id,
      value: values[id] ?? '',
      checked: false,
      textContent: '',
      disabled: false,
      placeholder: '',
      attrs: {},
      hidden: false,
      classes: new Set(),
      setAttribute(k, v) { this.attrs[k] = v },
      classList: {
        add: (c) => { elements[id].classes.add(c); if (c === 'hidden') elements[id].hidden = true },
        remove: (c) => { elements[id].classes.delete(c); if (c === 'hidden') elements[id].hidden = false },
        toggle: (c, on) => { elements[id].classes[on ? 'add' : 'delete'](c); if (c === 'hidden') elements[id].hidden = on },
      },
    })
  const record = (kind) => async (collection, ...args) => {
    calls.push([kind, collection, ...args])
    return { id: kind === 'create' ? `new-${calls.length}` : args[0] }
  }
  const api = { create: record('create'), patch: record('patch') }
  const ctx = {
    document: { getElementById: el },
    setTimeout,
    clearTimeout,
    api,
    agenciesMap: new Map(agencies.map((a) => [a.id, a])),
    clientsMap: new Map(clients.map((c) => [c.id, c])),
    editingAppId: editing,
    typeDrivenEdit: typeDriven,
    pendingEdit: pending,
    editingCompany: company,
    EVENT_LABELS,
    t,
    buildNotes,
    parseRecruiters,
    detectApplyType,
    closeForm() { ctx.closed = true },
    closed: false,
  }
  vm.createContext(ctx)
  vm.runInContext(`${dom}\n${extract('handleFormSubmit', true)}\n${extract('currentEvent')}\n${extract('eventFormTitle')}\n${extract('companyTitle')}\n${extract('updateCompanyHint')}\n${extract('updateKind')}\n${extract('pickCompany')}\nthis.hint = updateCompanyHint; this.submit = handleFormSubmit; this.kind = updateKind; this.pick = pickCompany; this.title = eventFormTitle; this.companyTitle = companyTitle`, ctx)
  const json = (x) => JSON.parse(JSON.stringify(x))
  return { ctx, calls: { all: () => json(calls) }, el, submit: () => ctx.submit({ preventDefault() {} }) }
}

const event = (calls) => calls.all().find(([, collection]) => collection === 'events')

test('a new agency is created, then the event is linked to it', async () => {
  const p = page({ fields: { 'f-company': 'Super Empresa', 'f-event': 'hr_intro', 'f-notes': ' call ' } })
  await p.submit()
  assert.deepEqual(p.calls.all(), [
    ['create', 'agencies', { name: 'Super Empresa' }],
    ['create', 'events', { date: '2026-10-08', time: null, event: 'hr_intro', agencyId: 'new-1', clientId: null, notes: 'call' }],
  ])
  assert.equal(p.ctx.closed, true)
})

test('an existing agency is found by name, ignoring case, and reused: nothing is created or renamed', async () => {
  const p = page({ agencies: [{ id: 'cwssg', name: 'CW Strategic Solutions Group' }], fields: { 'f-company': 'cw strategic solutions group' } })
  await p.submit()
  assert.deepEqual(p.calls.all().map((c) => c.slice(0, 2)), [['create', 'events']])
  assert.equal(event(p.calls)[2].agencyId, 'cwssg')
})

test('a client is created via its agency, or re-pointed to it when it exists and comes through another', async () => {
  const fresh = page({ agencies: [{ id: 'acme', name: 'Acme' }], fields: { 'f-company': 'Big Co', 'f-kind': 'client', 'f-via': 'Acme' } })
  await fresh.submit()
  assert.deepEqual(fresh.calls.all()[0], ['create', 'clients', { name: 'Big Co', viaAgencyId: 'acme' }])
  assert.deepEqual([event(fresh.calls)[2].agencyId, event(fresh.calls)[2].clientId], ['acme', 'new-1'])  // the event has both: Agency → Client

  const known = page({ agencies: [{ id: 'acme', name: 'Acme' }], clients: [{ id: 'big', name: 'Big Co' }], fields: { 'f-company': 'big co', 'f-kind': 'client', 'f-via': 'Acme' } })
  await known.submit()
  assert.deepEqual(known.calls.all()[0], ['patch', 'clients', 'big', { viaAgencyId: 'acme' }])
  assert.equal(event(known.calls)[2].clientId, 'big')

  const same = page({ agencies: [{ id: 'acme', name: 'Acme' }], clients: [{ id: 'big', name: 'Big Co', viaAgencyId: 'acme' }], fields: { 'f-company': 'Big Co', 'f-kind': 'client', 'f-via': 'Acme' } })
  await same.submit()
  assert.deepEqual(same.calls.all().map((c) => c.slice(0, 2)), [['create', 'events']])  // already there: nothing to write

  const newAgency = page({ fields: { 'f-company': 'Big Co', 'f-kind': 'client', 'f-via': 'Newco' } })
  await newAgency.submit()
  assert.deepEqual(newAgency.calls.all().slice(0, 2), [['create', 'agencies', { name: 'Newco' }], ['create', 'clients', { name: 'Big Co', viaAgencyId: 'new-1' }]])
})

test('a client with no agency is a direct one: created with none, or set to have none when it exists', async () => {
  const p = page({ fields: { 'f-company': 'Direct Co', 'f-kind': 'client', 'f-event': 'note' } })
  await p.submit()
  assert.deepEqual(p.calls.all()[0], ['create', 'clients', { name: 'Direct Co' }])
  const saved = event(p.calls)[2]
  assert.equal(saved.agencyId, null)
  assert.equal(saved.clientId, 'new-1')

  const known = page({ agencies: [{ id: 'acme', name: 'Acme' }], clients: [{ id: 'direct-co', name: 'Direct Co', viaAgencyId: 'acme' }], fields: { 'f-company': 'Direct Co', 'f-kind': 'client' } })
  await known.submit()
  assert.deepEqual(known.calls.all()[0], ['patch', 'clients', 'direct-co', { viaAgencyId: null }])
})

test('an event needs a company, a passive message may have a client alone, and a name that is the other tag is refused', async () => {
  const none = page({ fields: { 'f-company': '  ' } })
  await none.submit()
  assert.equal(none.el('form-error').textContent, 'Type the company.')
  assert.deepEqual(none.calls.all(), [])
  assert.equal(none.ctx.closed, false)

  const passive = page({ fields: { 'f-apply-type': 'passive', 'f-company': 'Big Co', 'f-kind': 'client' }, typeDriven: true })
  await passive.submit()
  assert.deepEqual([event(passive.calls)[2].event, event(passive.calls)[2].agencyId, event(passive.calls)[2].clientId], ['passive_message', null, 'new-1'])

  const clash = page({ agencies: [{ id: 'galgo', name: 'Galgo' }], fields: { 'f-company': 'galgo', 'f-kind': 'client' } })
  await clash.submit()
  assert.equal(clash.el('form-error').textContent, '"galgo" is already an agency.')
  assert.deepEqual(clash.calls.all(), [])

  const both = page({ agencies: [{ id: 'galgo', name: 'Galgo' }], clients: [{ id: 'galgo', name: 'Galgo' }], fields: { 'f-company': 'Galgo', 'f-kind': 'client' } })
  await both.submit()  // a name that is both already (from before) goes by the tag chosen
  assert.equal(event(both.calls)[2].clientId, 'galgo')
})

test('editing an event patches it instead of creating one', async () => {
  const p = page({ agencies: [{ id: 'acme', name: 'Acme' }], fields: { 'f-company': 'Acme', 'f-time': '10:30' }, editing: 'evt1' })
  await p.submit()
  assert.deepEqual(p.calls.all(), [['patch', 'events', 'evt1', { date: '2026-10-08', time: '10:30', event: 'note', agencyId: 'acme', clientId: null, notes: '' }]])
})

test('a refusal from the server shows in the form, which stays open and usable', async () => {
  const p = page({ agencies: [{ id: 'acme', name: 'Acme' }], fields: { 'f-company': 'Acme' } })
  p.ctx.api.create = async () => {
    throw new Error('A passive message needs an agency')
  }
  await p.submit()
  assert.equal(p.el('form-error').textContent, 'A passive message needs an agency')
  assert.ok(p.el('form-error').classes.has('is-open'), 'the error folds open')
  assert.equal(p.ctx.closed, false)
  assert.equal(p.el('form-submit').disabled, false)
  assert.equal(p.el('form-submit').textContent, 'Save')
})

test('typing the name of a company that exists picks it: its tag follows, and a client brings its agency', () => {
  const clients = [
    { id: 'big', name: 'Big Co', viaAgencyId: 'acme' },
    { id: 'solo', name: 'Solo Co', viaAgencyId: null },
  ]
  const p = page({ agencies: [{ id: 'acme', name: 'Acme' }], clients, fields: { 'f-company': 'big CO' } })
  p.ctx.pick()
  assert.deepEqual([p.el('f-kind').value, p.el('f-via').value, p.el('f-via').hidden], ['client', 'Acme', false])

  p.el('f-company').value = 'Solo Co'
  p.ctx.pick()
  assert.deepEqual([p.el('f-kind').value, p.el('f-via').value], ['client', ''])

  p.el('f-company').value = 'ACME'
  p.ctx.pick()
  assert.deepEqual([p.el('f-kind').value, p.el('f-via').hidden], ['agency', true])  // Via agency is only for a client

  // a name that is not known is a new company: the tag stays as it was
  p.el('f-kind').value = 'client'
  p.el('f-company').value = 'Brand New Co'
  p.ctx.pick()
  assert.equal(p.el('f-kind').value, 'client')
})

test('the form says which typed companies are new, as soon as they are typed, and when a name is the other tag', () => {
  const p = page({ agencies: [{ id: 'acme', name: 'Acme' }], clients: [{ id: 'big', name: 'Big Co', viaAgencyId: 'acme' }], fields: { 'f-company': 'acme' } })
  p.ctx.hint()
  assert.equal(p.el('f-company-hint').textContent, '') // Acme exists, ignoring case
  assert.ok(!p.el('f-company-hint').classes.has('is-open'))

  p.el('f-company').value = 'Newco'
  p.ctx.hint()
  assert.equal(p.el('f-company-hint').textContent, 'Will create the new agency "Newco".')
  assert.ok(p.el('f-company-hint').classes.has('is-open'), 'the hint folds open')

  p.el('f-kind').value = 'client'
  p.el('f-company').value = 'Brand New Co'
  p.el('f-via').value = 'Newco' // typing the agency a client comes via runs the hint too
  p.ctx.hint()
  assert.equal(p.el('f-company-hint').textContent, 'Will create the new agency "Newco" and the new client "Brand New Co".')

  p.el('f-company').value = 'big co' // a known client brings its agency, so nothing is new any more
  p.ctx.pick()
  assert.equal(p.el('f-via').value, 'Acme')
  assert.ok(!p.el('f-company-hint').classes.has('is-open'), 'the hint folds away') // its text goes once it is folded

  p.el('f-company').value = 'Acme' // its tag follows once it is typed, so changing it by hand is what clashes
  p.ctx.pick()
  p.el('f-kind').value = 'client'
  p.ctx.kind()
  assert.equal(p.el('f-company-hint').textContent, '"Acme" is already an agency.')
})

test('an edit form is titled "{Company} → {Event}", the event following the Type or the Event select', () => {
  const title = (editing, typeDriven, fields = {}) => page({ editing, typeDriven, fields, company: 'Northwind Staffing' }).ctx.title()
  assert.equal(title(null, false), 'Update')
  assert.equal(title('evt1', true, { 'f-apply-type': 'email_apply' }), 'Northwind Staffing → Application')
  assert.equal(title('evt1', true, { 'f-apply-type': 'web_form' }), 'Northwind Staffing → Application')
  assert.equal(title('evt1', true, { 'f-apply-type': 'passive' }), 'Northwind Staffing → Passive')
  assert.equal(title('evt1', false, { 'f-event': 'hr_intro' }), 'Northwind Staffing → HR Intro')
  assert.equal(title('evt1', false, { 'f-event': 'red_flag' }), 'Northwind Staffing → Red Flag')
})

test('the company in the title is the agency, with the client in parentheses when the event has both', () => {
  const p = page({ clients: [{ id: 'big', name: 'Big Co' }] })
  assert.equal(p.ctx.companyTitle({ agencyId: 'acme', clientId: 'big', companyLabel: 'Acme' }), 'Acme (Big Co)')
  assert.equal(p.ctx.companyTitle({ agencyId: null, clientId: 'big', companyLabel: 'Big Co' }), 'Big Co')
  assert.equal(p.ctx.companyTitle({ agencyId: 'acme', clientId: null, companyLabel: 'Acme' }), 'Acme')
  assert.equal(p.ctx.companyTitle({ agencyId: null, clientId: null, companyLabel: '' }), '—')
})

test('creating an event sends no link; only an application or passive message goes by its Type and sends its link', async () => {
  const created = page({ agencies: [{ id: 'acme', name: 'Acme' }], fields: { 'f-company': 'Acme', 'f-jd': 'https://ignored.example', 'f-apply-type': 'web_form', 'f-recruiter': 'ignored' } })
  await created.submit()
  const body = created.calls.all()[0][2]
  assert.ok(!('jdUrl' in body) && !('applyType' in body))
  assert.equal(body.notes, '')

  const edit = async (fields, typeDriven = true) => {
    const p = page({ agencies: [{ id: 'acme', name: 'Acme' }], fields: { 'f-company': 'Acme', ...fields }, editing: 'evt1', typeDriven })
    await p.submit()
    return p.calls.all()[0][3]
  }
  const email = await edit({ 'f-jd': 'https://jobs.example/x', 'f-apply-type': 'email_apply', 'f-recruiter': 'https://www.linkedin.com/in/someone/\n\nhttps://www.linkedin.com/in/other/', 'f-notes': 'a note' })
  assert.deepEqual([email.event, email.applyType, email.jdUrl], ['application', 'email_apply', 'https://jobs.example/x'])  // the type is its own field, not taken from the link
  assert.equal(email.notes, 'Recruiter: https://www.linkedin.com/in/someone/\nRecruiter: https://www.linkedin.com/in/other/\na note')

  const web = await edit({ 'f-jd': ' https://jobs.example/web ', 'f-apply-type': 'web_form', 'f-notes': 'just notes' })
  assert.deepEqual([web.event, web.applyType, web.jdUrl, web.notes], ['application', 'web_form', 'https://jobs.example/web', 'just notes'])

  const emailNoLink = await edit({ 'f-jd': '  ', 'f-apply-type': 'email_apply' })
  assert.deepEqual([emailNoLink.applyType, emailNoLink.jdUrl], ['email_apply', null])

  const passive = await edit({ 'f-jd': 'https://dropped.example', 'f-apply-type': 'passive', 'f-recruiter': 'https://www.linkedin.com/in/someone/' })
  assert.deepEqual([passive.event, passive.applyType, passive.jdUrl], ['passive_message', null, null])  // a passive message has no link or apply type

  // any other event has no link, apply type or recruiters in its form: none of them is sent
  const note = await edit({ 'f-event': 'hr_intro', 'f-jd': 'https://x.example', 'f-apply-type': 'web_form', 'f-recruiter': 'ignored', 'f-notes': 'plain' }, false)
  assert.deepEqual([note.event, 'jdUrl' in note, 'applyType' in note, note.notes], ['hr_intro', false, false, 'plain'])
})

test('an application of type Web needs its Application link when edited, an email one does not', async () => {
  const web = page({ agencies: [{ id: 'acme', name: 'Acme' }], fields: { 'f-company': 'Acme', 'f-apply-type': 'web_form', 'f-jd': '  ' }, editing: 'evt1', typeDriven: true })
  await web.submit()
  assert.equal(web.el('form-error').textContent, 'The Application link is required for a web application.')
  assert.deepEqual(web.calls.all(), [])

  const email = page({ agencies: [{ id: 'acme', name: 'Acme' }], fields: { 'f-company': 'Acme', 'f-apply-type': 'email_apply', 'f-jd': '' }, editing: 'evt1', typeDriven: true })
  await email.submit()
  assert.equal(email.calls.all()[0][3].jdUrl, null)
})

test('an application changed to passive keeps its client: a passive message needs a company, not an agency', async () => {
  const p = page({ clients: [{ id: 'big', name: 'Big Co' }], fields: { 'f-company': 'Big Co', 'f-kind': 'client', 'f-apply-type': 'passive' }, editing: 'evt1', typeDriven: true })
  await p.submit()
  assert.deepEqual(p.calls.all().map((c) => c.slice(0, 3)), [['patch', 'events', 'evt1']])
  const saved = p.calls.all()[0][3]
  assert.deepEqual([saved.event, saved.agencyId, saved.clientId], ['passive_message', null, 'big'])
})

// Runs the real fillEventSelect and handleFormDelete out of main.js.
function formParts({ confirmed = true, fail = null } = {}) {
  const removed = []
  const select = { innerHTML: '' }
  const errorEl = { textContent: '', classes: new Set(), classList: { add: (c) => errorEl.classes.add(c), remove: (c) => errorEl.classes.delete(c) } }
  const ctx = {
    document: { getElementById: (id) => (id === 'f-event' ? select : errorEl) },
    t,
    setTimeout,
    clearTimeout,
    EVENT_TYPES: ['application', 'passive_message', 'note', 'archive'],
    EVENT_LABELS: { application: { emoji: '📝', label: 'Application' }, passive_message: { emoji: '📩', label: 'Passive message' }, note: { emoji: '🗒️', label: 'Note' }, archive: { emoji: '📦', label: 'Archive' }, pending: { emoji: '⏳', label: 'Pending' } },
    editingAppId: 'evt1',
    api: { remove: async (collection, id) => { if (fail) throw new Error(fail); removed.push([collection, id]) } },
    confirm: () => confirmed,
    closeForm() { ctx.closed = true },
    closed: false,
  }
  vm.createContext(ctx)
  vm.runInContext(`${dom}\nvar LOCKED_TYPES = ['application', 'passive_message', 'archive', 'pending']\n${extract('fillEventSelect')}\n${extract('handleFormDelete', true)}\nthis.fill = fillEventSelect; this.del = handleFormDelete`, ctx)
  return { ctx, select, errorEl, removed }
}

test('Application, Passive message, Archive and Pending are not types of "+ Update", and one being edited offers only itself', () => {
  const creating = formParts()
  creating.ctx.fill(null)
  for (const type of ['application', 'passive_message', 'archive', 'pending']) assert.ok(!creating.select.innerHTML.includes(`value="${type}"`), type)
  assert.ok(creating.select.innerHTML.includes('value="note"'))

  for (const type of ['application', 'archive', 'pending']) {
    const editing = formParts()
    editing.ctx.fill(type)
    assert.ok(editing.select.innerHTML.includes(`value="${type}"`))
    assert.ok(!editing.select.innerHTML.includes('value="note"'), `the type of ${type} can't be changed`)
  }
})

test('a queued link is edited as just its date, time, link and notes, with no company asked for', async () => {
  const p = page({ editing: 'p1', pending: true, fields: { 'f-event': 'pending', 'f-company': '', 'f-jd': ' https://jobs.example/new ', 'f-notes': ' queued ', 'f-time': '09:15' } })
  await p.submit()
  assert.deepEqual(p.calls.all(), [['patch', 'events', 'p1', { date: '2026-10-08', time: '09:15', notes: 'queued', jdUrl: 'https://jobs.example/new', applyType: 'web_form' }]])
  assert.equal(p.ctx.closed, true)

  const mail = page({ editing: 'p1', pending: true, fields: { 'f-event': 'pending', 'f-jd': 'jobs@acme.example' } })
  await mail.submit()
  assert.equal(mail.calls.all()[0][3].applyType, 'email_apply')

  const blank = page({ editing: 'p1', pending: true, fields: { 'f-event': 'pending', 'f-jd': '  ' } })
  await blank.submit()
  assert.deepEqual([blank.calls.all()[0][3].jdUrl, blank.calls.all()[0][3].applyType], [null, null])
})

test('the event types are listed A-Z by name, in Update and in Edit', () => {
  const select = { innerHTML: '' }
  const ctx = { document: { getElementById: () => select }, EVENT_TYPES, EVENT_LABELS }
  vm.createContext(ctx)
  vm.runInContext(`var LOCKED_TYPES = ['application', 'passive_message', 'archive', 'pending']\n${extract('fillEventSelect')}\nthis.fill = fillEventSelect`, ctx)
  ctx.fill(null)
  const names = [...select.innerHTML.matchAll(/<option value="[^"]+">[^ ]+ ([^<]+)<\/option>/g)].map((m) => m[1])
  assert.ok(names.length >= 8, names.join(', '))
  assert.deepEqual(names, [...names].sort((a, b) => a.localeCompare(b)))
  assert.equal(names[0], 'Culture Interview')
  assert.ok(!names.includes('AI interview') && !names.includes('Video task'), 'those two types are gone')
  assert.ok(names.includes('Culture Interview') && names.includes('Technical interview'))
  assert.ok(!names.includes('Application') && !names.includes('Archive') && !names.includes('Passive message'))
})

test('the Type options (Email, Passive, Web) are listed A-Z in "+ Application" and in Edit', () => {
  const html = readFileSync(new URL('../../public/index.html', import.meta.url), 'utf8')
  const select = /<select id="app-type"[\s\S]*?<\/select>/.exec(html)[0]
  // the labels are filled in by the page from the locale file: the markup holds the values, and the keys of their texts
  const inForm = [...select.matchAll(/<option value="([^"]+)"[^>]*data-i18n="([^"]+)"/g)].map((m) => [m[1], m[2]])
  assert.deepEqual(inForm, [['email_apply', 'app.typeEmail'], ['passive', 'app.typePassive'], ['web_form', 'app.typeWeb']])
  assert.deepEqual(inForm.map(([, key]) => t(key)), ['Email', 'Passive', 'Web'])

  const el = { innerHTML: '', value: '' }
  const ctx = { document: { getElementById: () => el }, t }
  vm.createContext(ctx)
  vm.runInContext(`${extract('fillApplyType')}\nthis.fill = fillApplyType`, ctx)
  ctx.fill('web_form')
  assert.deepEqual([...el.innerHTML.matchAll(/>([^<]+)<\/option>/g)].map((m) => m[1]), ['Email', 'Passive', 'Web'])
  ctx.fill('')  // an application with no type yet shows a blank one first, then the rest A-Z
  assert.deepEqual([...el.innerHTML.matchAll(/>([^<]+)<\/option>/g)].map((m) => m[1]), ['—', 'Email', 'Passive', 'Web'])
})

test('archives and queued links are not shown in the Calendar, and everything else is', () => {
  const ctx = {}
  vm.createContext(ctx)
  vm.runInContext(`${extract('shownInCalendar')}\nthis.shown = shownInCalendar`, ctx)
  const events = ['application', 'passive_message', 'hr_intro', 'note', 'rejection', 'pending', 'archive']
  assert.deepEqual(events.filter((event) => ctx.shown({ event })), ['application', 'passive_message', 'hr_intro', 'note', 'rejection'])
  assert.ok(/applications\.filter\(shownInCalendar\)/.test(mainSource), 'the week is built from the filtered events')
})

test('the form opens with the time the event has, or the current one, and the buttons are in order', () => {
  assert.ok(/getElementById\('f-time'\)\.value = formTime\(app\?\.time\)/.test(mainSource), 'openForm puts back the time of the event being edited')
  const html = readFileSync(new URL('../../public/index.html', import.meta.url), 'utf8')
  const at = (id) => html.indexOf(`id="${id}"`)
  assert.ok(at('new-application-btn') > 0 && at('new-application-btn') < at('new-event-btn') && at('new-event-btn') < at('weekly-report-btn'))
})

test('deleting an event asks first, removes it and closes the form; a refusal stays in the form', async () => {
  const yes = formParts()
  await yes.ctx.del()
  assert.deepEqual(yes.removed, [['events', 'evt1']])
  assert.equal(yes.ctx.closed, true)

  const no = formParts({ confirmed: false })
  await no.ctx.del()
  assert.deepEqual(no.removed, [])
  assert.equal(no.ctx.closed, false)

  const refused = formParts({ fail: 'The server said no' })
  await refused.ctx.del()
  assert.equal(refused.errorEl.textContent, 'The server said no')
  assert.equal(refused.ctx.closed, false)
})

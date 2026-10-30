// The texts of the page (public/js/i18n.js and public/locales/*.json): both languages say the same things, nothing
// asks for a text that does not exist, and the language is the one in Settings, English when it can't be known.
// Run with: node --import ./tests/js/setup.mjs --test tests/js
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { test } from 'node:test'

const PUBLIC = new URL('../../public/', import.meta.url)
const read = (path) => readFileSync(new URL(path, PUBLIC), 'utf8')
const locale = (lang) => JSON.parse(read(`locales/${lang}.json`))
const en = locale('en')
const es = locale('es')
const placeholders = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

const { LANGUAGES, initI18n, t, translatePage } = await import('../../public/js/i18n.js')

// ---------- the files ----------

test('English and Spanish have exactly the same keys', () => {
  const missingInSpanish = Object.keys(en).filter((k) => !(k in es))
  const missingInEnglish = Object.keys(es).filter((k) => !(k in en))
  assert.deepEqual({ missingInSpanish, missingInEnglish }, { missingInSpanish: [], missingInEnglish: [] })
})

test('no text is empty, and each key keeps its {placeholders} in both languages', () => {
  for (const [key, text] of Object.entries(en)) {
    assert.ok(text.trim() && es[key].trim(), `${key} is empty`)
    assert.deepEqual(placeholders(es[key]), placeholders(text), `${key}: the placeholders differ`)
  }
})

test('the keys are flat and written in the same style', () => {
  for (const key of Object.keys(en)) assert.match(key, /^[a-zA-Z]+(\.[A-Za-z0-9_]+)+$/, key)
})

// ---------- the code against the files ----------

const files = readdirSync(new URL('js/', PUBLIC)).filter((f) => f.endsWith('.js')).map((f) => `js/${f}`)
const code = [...files, 'index.html', 'navigation/questions.html'].map(read).join('\n')

test('every text the code asks for by name exists', () => {
  const asked = new Set([
    ...[...code.matchAll(/\bt\(\s*['"`]([\w.]+)['"`]/g)].map((m) => m[1]),
    ...[...code.matchAll(/data-i18n(?:-[a-z-]+)?=["']([\w.]+)["']/g)].map((m) => m[1]),
  ])
  assert.ok(asked.size > 100, 'the scan found the texts')
  assert.deepEqual([...asked].filter((key) => !(key in en)), [])
})

test('every key is used, except the families the code builds the name of', () => {
  const built = ['events.', 'settings.var.', 'settings.choice.', 'report.q.', 'date.', 'hint.', 'companies.closedBy.']
  const unused = Object.keys(en).filter((key) => !built.some((prefix) => key.startsWith(prefix)) && !code.includes(key))
  assert.deepEqual(unused, [])
})

test('the families built from a name have every member: each event type, each setting, each choice', async () => {
  const { EVENT_TYPES } = await import('../../public/js/events.js')
  for (const type of [...EVENT_TYPES, 'pending']) assert.ok(`events.${type}` in en, `events.${type}`)
  const names = ['APP_LANGUAGE', 'CV_PDF_PATH', 'EMAIL_ADDRESS', 'EMAIL_PASSWORD', 'EMAIL_SMTP_HOST', 'EMAIL_SMTP_PORT', 'GEMINI_API_KEY', 'GOOGLE_CALENDAR_ID', 'GOOGLE_TASKS_CLIENT_ID', 'GOOGLE_TASKS_CLIENT_SECRET', 'GOOGLE_TASKS_REFRESH_TOKEN']
  for (const name of names) for (const part of ['label', 'description']) assert.ok(`settings.var.${name}.${part}` in en, `settings.var.${name}.${part}`)
  for (const closedBy of ['ghosted', 'rejection', 'red_flag', 'on_hold', 'offer']) assert.ok(`companies.closedBy.${closedBy}` in en, closedBy)
  for (const lang of LANGUAGES) assert.ok(`settings.choice.APP_LANGUAGE.${lang}` in en, lang)
  for (const q of ['hrTalked', 'hiddenMarket', 'byMail', 'byPlatform', 'passiveInterviews', 'hrInterviews', 'techInterviews', 'cultureInterviews', 'offers']) {
    assert.ok(`report.q.${q}` in en, q)
  }
})

// ---------- t() and the language ----------

function fakeNode(attributes = {}) {
  const node = { dataset: {}, attrs: {}, textContent: '', innerHTML: '', setAttribute: (k, v) => (node.attrs[k] = v) }
  for (const [name, value] of Object.entries(attributes)) node.dataset[name] = value
  return node
}

function fakePage(nodes = {}) {
  return { documentElement: { lang: '' }, querySelectorAll: (selector) => nodes[selector] ?? [] }
}

// A fetch that serves the given locale files and says which language Settings has (undefined: none saved).
function serve({ settings, files = { en, es } }) {
  globalThis.fetch = async (url) => {
    if (url === '/api/settings/env') {
      if (settings === 'down') throw new Error('offline')
      return { ok: true, json: async () => (settings ? [{ name: 'APP_LANGUAGE', value: settings }] : [{ name: 'APP_LANGUAGE', value: null }]) }
    }
    const lang = /locales\/(\w+)\.json/.exec(url)?.[1]
    return files[lang] ? { ok: true, json: async () => files[lang] } : { ok: false, json: async () => ({}) }
  }
}

test('English is the language until Settings says another one', async () => {
  globalThis.document = fakePage()
  serve({ settings: undefined })
  await initI18n()
  assert.equal(t('nav.calendar'), en['nav.calendar'])
  assert.equal(document.documentElement.lang, 'en')
})

test('Spanish comes from the APP_LANGUAGE setting, and the page says which language it is in', async () => {
  globalThis.document = fakePage()
  serve({ settings: 'es' })
  await initI18n()
  assert.equal(t('nav.calendar'), es['nav.calendar'])
  assert.notEqual(es['nav.calendar'], en['nav.calendar'])
  assert.equal(document.documentElement.lang, 'es')
})

test('a language that does not exist, or a server that does not answer, means English', async () => {
  for (const settings of ['fr', 'ES', '', 'down']) {
    globalThis.document = fakePage()
    serve({ settings })
    await initI18n()
    assert.equal(document.documentElement.lang, 'en', String(settings))
    assert.equal(t('nav.calendar'), en['nav.calendar'])
  }
})

test('a key the chosen language does not have yet is shown in English', async () => {
  globalThis.document = fakePage()
  const partial = { ...es }
  delete partial['nav.calendar']
  serve({ settings: 'es', files: { en, es: partial } })
  await initI18n()
  assert.equal(t('nav.calendar'), en['nav.calendar'])
  assert.equal(t('nav.settings'), es['nav.settings'])
})

test('a placeholder is filled in, one that is not given stays as it is, and an unknown key is the key or the text given', async () => {
  globalThis.document = fakePage()
  serve({ settings: undefined })
  await initI18n()
  assert.equal(t('pending.count', { count: 3 }), '3 queued')
  assert.equal(t('pending.count'), '{count} queued')
  assert.equal(t('no.such.key'), 'no.such.key')
  assert.equal(t('no.such.key', {}, 'Text from the server'), 'Text from the server')
})

test('the static page is translated: text, html, placeholder, title and aria-label', async () => {
  const nodes = {
    '[data-i18n]': [fakeNode({ i18n: 'nav.calendar' })],
    '[data-i18n-html]': [fakeNode({ i18nHtml: 'pending.queueHelp' })],
    '[data-i18n-placeholder]': [fakeNode({ i18nPlaceholder: 'pending.placeholder' })],
    '[data-i18n-title]': [fakeNode({ i18nTitle: 'pending.editOrDelete' })],
    '[data-i18n-aria-label]': [fakeNode({ i18nAriaLabel: 'pending.editOrDelete' })],
  }
  serve({ settings: 'es' })
  globalThis.document = fakePage(nodes)
  await initI18n()
  assert.equal(nodes['[data-i18n]'][0].textContent, es['nav.calendar'])
  assert.equal(nodes['[data-i18n-html]'][0].innerHTML, es['pending.queueHelp'])
  assert.equal(nodes['[data-i18n-placeholder]'][0].attrs.placeholder, es['pending.placeholder'])
  assert.equal(nodes['[data-i18n-title]'][0].attrs.title, es['pending.editOrDelete'])
  assert.equal(nodes['[data-i18n-aria-label]'][0].attrs['aria-label'], es['pending.editOrDelete'])
  const again = fakeNode({ i18n: 'nav.settings' })
  translatePage({ querySelectorAll: (selector) => (selector === '[data-i18n]' ? [again] : []) })  // a part of the page, drawn later
  assert.equal(again.textContent, es['nav.settings'])
})

test('every data-i18n in the page names a text that exists', () => {
  const html = read('index.html')
  const names = [...html.matchAll(/data-i18n(?:-[a-z-]+)?="([^"]+)"/g)].map((m) => m[1])
  assert.ok(names.length > 50)
  assert.deepEqual([...new Set(names)].filter((n) => !(n in en)), [])
})

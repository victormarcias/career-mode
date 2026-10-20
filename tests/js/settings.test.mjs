// The Settings page's pure parts (public/js/settings.js): what gets saved, and how a field is drawn.
// Run with: node --test tests/js
import assert from 'node:assert/strict'
import { test } from 'node:test'

globalThis.fetch = async () => {
  throw new Error('no network in these tests')
}
const { codeHtml, envPayload, fieldHtml, toggleReveal } = await import('../../public/js/settings.js')

const key = { name: 'GEMINI_API_KEY', label: 'Gemini API key', description: 'd', secret: true, restartRequired: false, default: null, isSet: true, value: null, length: 12 }
const port = { name: 'EMAIL_SMTP_PORT', label: 'SMTP port', description: 'd', secret: false, restartRequired: true, default: '465', isSet: true, value: '587', length: null }
const host = { name: 'EMAIL_SMTP_HOST', label: 'SMTP server', description: 'd', secret: false, restartRequired: true, default: 'smtp.gmail.com', isSet: false, value: null, length: null }
const vars = [key, port, host]

test('nothing is sent when nothing changed', () => {
  assert.deepEqual(envPayload(vars, { GEMINI_API_KEY: { typed: '' }, EMAIL_SMTP_PORT: { typed: '587' }, EMAIL_SMTP_HOST: { typed: '' } }), {})
})

test('a secret left empty is kept, a new one replaces it, and one emptied after looking at it is removed', () => {
  assert.deepEqual(envPayload(vars, { GEMINI_API_KEY: { typed: '  ' } }), {})
  assert.deepEqual(envPayload(vars, { GEMINI_API_KEY: { typed: ' new-key ' } }), { GEMINI_API_KEY: 'new-key' })
  // emptied after the eye showed it (the page then knows what it was): it is removed
  assert.deepEqual(envPayload(vars, { GEMINI_API_KEY: { typed: '', original: 'AIzaTheRealKey' } }), { GEMINI_API_KEY: null })
})

test('only plain values that changed are sent, and emptying one removes it', () => {
  assert.deepEqual(envPayload(vars, { EMAIL_SMTP_PORT: { typed: '2525' }, EMAIL_SMTP_HOST: { typed: ' smtp.example.org ' } }), { EMAIL_SMTP_PORT: '2525', EMAIL_SMTP_HOST: 'smtp.example.org' })
  assert.deepEqual(envPayload(vars, { EMAIL_SMTP_PORT: { typed: '' } }), { EMAIL_SMTP_PORT: null })
  assert.deepEqual(envPayload([host], { EMAIL_SMTP_HOST: { typed: '' } }), {}) // it was already unset
})

test('a variable the form did not report is left alone, not read as emptied', () => {
  assert.deepEqual(envPayload(vars, {}), {})
  assert.deepEqual(envPayload(vars, { GEMINI_API_KEY: { typed: 'k' } }), { GEMINI_API_KEY: 'k' })
})

test('a secret field never contains the secret: only dots and a hidden input', () => {
  const html = fieldHtml(key)
  assert.match(html, /type="password"/)
  assert.match(html, /placeholder="•{12}"/) // as many dots as the secret has characters, and nothing else
  assert.doesNotMatch(html, /placeholder="•{13}|placeholder="•{11}"/)
  assert.doesNotMatch(html, /type a new one|\(set\)/)
  assert.match(fieldHtml({ ...key, length: 53 }), new RegExp('placeholder="•{53}"'))
  assert.doesNotMatch(html, /value=/)
  assert.match(html, /data-is-set="true"/)
  assert.match(fieldHtml({ ...key, isSet: false, length: null }), /data-is-set="false"/)
})

test('a plain field shows its value, its default as the hint, and the restart badge', () => {
  const html = fieldHtml(port)
  assert.match(html, /value="587"/)
  assert.match(html, /placeholder="465"/)
  assert.match(html, /Applies after a restart/)
  assert.doesNotMatch(fieldHtml(key), /Applies after a restart/)
})

test('what comes from the server is escaped', () => {
  const html = fieldHtml({ ...port, label: '<b>x</b>', value: '"><script>', description: '<i>d</i>' })
  assert.doesNotMatch(html, /<script>|<b>x|<i>d/)
})

// ---------- the eye ----------

const input = (extra = {}) => ({ name: 'GEMINI_API_KEY', type: 'password', value: '', dataset: { isSet: 'true' }, ...extra })
const secretFetcher = (value = 'AIzaTheRealKey') => {
  const calls = []
  const fetcher = async (name) => {
    calls.push(name)
    return { name, value }
  }
  return { fetcher, calls }
}

test('only a secret field has an eye, and the field starts hidden', () => {
  const html = fieldHtml(key)
  assert.match(html, /data-reveal="GEMINI_API_KEY"/)
  assert.match(html, /data-icon="show"/)
  assert.match(html, /data-icon="hide"/)
  assert.match(html, /type="password"/)
  assert.doesNotMatch(fieldHtml(port), /data-reveal/)
  assert.doesNotMatch(fieldHtml(host), /data-reveal/)
})

test('the first click loads the real value from the server and shows it', async () => {
  const field = input()
  const { fetcher, calls } = secretFetcher()
  assert.equal(await toggleReveal(field, fetcher), true)
  assert.deepEqual(calls, ['GEMINI_API_KEY'])
  assert.equal(field.value, 'AIzaTheRealKey')
  assert.equal(field.type, 'text')
  assert.equal(field.dataset.original, 'AIzaTheRealKey')
})

test('hiding it again does not ask the server again, and showing it again neither', async () => {
  const field = input()
  const { fetcher, calls } = secretFetcher()
  await toggleReveal(field, fetcher)
  assert.equal(await toggleReveal(field, fetcher), false)
  assert.equal(field.type, 'password')
  assert.equal(field.value, 'AIzaTheRealKey') // still there, just hidden
  assert.equal(await toggleReveal(field, fetcher), true)
  assert.equal(calls.length, 1)
})

test('what you are typing is shown as it is, without asking the server', async () => {
  const typing = input({ value: 'new-key-being-typed' })
  const { fetcher, calls } = secretFetcher()
  assert.equal(await toggleReveal(typing, fetcher), true)
  assert.equal(typing.value, 'new-key-being-typed')
  assert.equal(calls.length, 0)

  const unset = input({ dataset: { isSet: 'false' } })
  assert.equal(await toggleReveal(unset, fetcher), true) // nothing stored: it just reveals the empty field
  assert.equal(calls.length, 0)
})

test('if the server refuses, the field stays hidden and the error comes through', async () => {
  const field = input()
  await assert.rejects(toggleReveal(field, async () => { throw new Error('boom') }), { message: 'boom' })
  assert.equal(field.type, 'password')
  assert.equal(field.value, '')
})

test('saving after only looking sends nothing; editing what the eye loaded does', () => {
  const looked = { GEMINI_API_KEY: { typed: 'AIzaTheRealKey', original: 'AIzaTheRealKey' } }
  assert.deepEqual(envPayload([key], looked), {})
  assert.deepEqual(envPayload([key], { GEMINI_API_KEY: { typed: 'AIzaChanged', original: 'AIzaTheRealKey' } }), { GEMINI_API_KEY: 'AIzaChanged' })
  assert.deepEqual(envPayload([key], { GEMINI_API_KEY: { typed: '', original: 'AIzaTheRealKey' } }), { GEMINI_API_KEY: null })
})

// ---------- filenames and commands as code ----------

test('text between backticks becomes code, the rest is plain', () => {
  const html = codeHtml('Used by the `daily-post` skill (`scripts/generate_daily_image.py`) to draw it.')
  assert.equal((html.match(/<code /g) ?? []).length, 2)
  assert.match(html, /<code [^>]*>daily-post<\/code> skill \(<code [^>]*>scripts\/generate_daily_image\.py<\/code>\) to draw it\./)
  assert.doesNotMatch(html, /`/)
})

test('everything else in the text is escaped, inside and outside the code', () => {
  const html = codeHtml('<b>x</b> and `<i>y</i> & z`')
  assert.doesNotMatch(html, /<b>|<i>/)
  assert.match(html, /&lt;b&gt;x&lt;\/b&gt; and <code [^>]*>&lt;i&gt;y&lt;\/i&gt; &amp; z<\/code>/)
})

test('a lone backtick, or one that spans lines, is left as it is', () => {
  assert.equal(codeHtml('a ` b'), 'a ` b')
  assert.doesNotMatch(codeHtml('a `b\nc` d'), /<code/)
})

test('the field descriptions show their filenames and the default as code', () => {
  // a name the locale files do not know, so the description given is the one shown
  const html = fieldHtml({ ...key, name: 'SOME_NEW_VARIABLE', description: 'Used by the `daily-post` skill (`scripts/generate_daily_image.py`).' })
  assert.match(html, /<code [^>]*>scripts\/generate_daily_image\.py<\/code>/)
  assert.match(fieldHtml(port), /Default: <code [^>]*>465<\/code>\./)
})

// ---------- the language ----------

const language = { name: 'APP_LANGUAGE', label: 'Language', description: 'd', secret: false, restartRequired: false, default: 'en', choices: ['en', 'es'], isSet: false, value: null, length: null }

test('a choice is a list, with English selected until one is saved', () => {
  const html = fieldHtml(language)
  assert.match(html, /<select id="env-APP_LANGUAGE" name="APP_LANGUAGE"/)
  assert.match(html, /<option value="en" selected>English<\/option>/)
  assert.match(html, /<option value="es">Español<\/option>/)
  assert.match(fieldHtml({ ...language, isSet: true, value: 'es' }), /<option value="es" selected>/)
})

test('a choice is sent only when it differs from what is saved, or from English when nothing is', () => {
  assert.deepEqual(envPayload([language], { APP_LANGUAGE: { typed: 'en' } }), {})
  assert.deepEqual(envPayload([language], { APP_LANGUAGE: { typed: 'es' } }), { APP_LANGUAGE: 'es' })
  assert.deepEqual(envPayload([{ ...language, isSet: true, value: 'es' }], { APP_LANGUAGE: { typed: 'es' } }), {})
  assert.deepEqual(envPayload([{ ...language, isSet: true, value: 'es' }], { APP_LANGUAGE: { typed: 'en' } }), { APP_LANGUAGE: 'en' })
})

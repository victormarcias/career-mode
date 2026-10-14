// Loaded before every front-end test (node --import): the app writes its texts with t(), so the tests read them in
// English, from the same public/locales/en.json the page loads. Run with: node --import ./tests/js/setup.mjs --test tests/js
import { readFile } from 'node:fs/promises'

const locales = new URL('../../public/locales/', import.meta.url)
const realFetch = globalThis.fetch

globalThis.fetch = async (url, ...rest) => {
  const path = String(url)
  if (path.startsWith('locales/')) return { ok: true, json: async () => JSON.parse(await readFile(new URL(path.slice('locales/'.length), locales), 'utf8')) }
  if (path === '/api/settings/env') return { ok: true, json: async () => [] } // no APP_LANGUAGE set: English
  return realFetch(url, ...rest)
}

// initI18n also sets <html lang> and translates the page: a stand-in document is enough for that, and it goes away after.
const hadDocument = 'document' in globalThis
if (!hadDocument) globalThis.document = { documentElement: {}, querySelectorAll: () => [] }
const { initI18n } = await import('../../public/js/i18n.js')
await initI18n()
if (!hadDocument) delete globalThis.document

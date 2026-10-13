// Translations: one file per language in public/locales/ (en.json, es.json), each a flat {"key": "text"}, like the
// .strings files of iOS. English is the default and the fallback for a key a language does not have yet. The
// language is the APP_LANGUAGE setting, read when the page loads (a change in Settings reloads the page).
//
//   t('calendar.thisWeek')                      a text, or the key itself when no file has it
//   t('pending.count', { count: 3 })            "{count} queued" -> "3 queued"
//   <span data-i18n="nav.calendar"></span>      static HTML, filled by translatePage (also data-i18n-html,
//                                               data-i18n-placeholder, data-i18n-title and data-i18n-aria-label)

export const LANGUAGES = ['en', 'es']
let language = 'en'
let strings = {}
let fallback = {}

async function load(lang) {
  const response = await fetch(`locales/${lang}.json`)
  return response.ok ? response.json() : {}
}

async function chosenLanguage() {
  try {
    const vars = await fetch('/api/settings/env').then((response) => response.json())
    const value = vars.find((v) => v.name === 'APP_LANGUAGE')?.value
    return LANGUAGES.includes(value) ? value : 'en'
  } catch {
    return 'en'
  }
}

export async function initI18n() {
  language = await chosenLanguage()
  fallback = await load('en')
  strings = language === 'en' ? fallback : { ...fallback, ...(await load(language)) }
  document.documentElement.lang = language
  translatePage(document)
}

// `fallbackText` is shown when no file has the key (a text that comes from the server, for instance).
export function t(key, vars = {}, fallbackText = key) {
  const text = strings[key] ?? fallback[key] ?? fallbackText
  return text.replace(/\{(\w+)\}/g, (_, name) => (name in vars ? vars[name] : `{${name}}`))
}

export function translatePage(root = document) {
  root.querySelectorAll('[data-i18n]').forEach((el) => (el.textContent = t(el.dataset.i18n)))
  root.querySelectorAll('[data-i18n-html]').forEach((el) => (el.innerHTML = t(el.dataset.i18nHtml)))
  root.querySelectorAll('[data-i18n-placeholder]').forEach((el) => el.setAttribute('placeholder', t(el.dataset.i18nPlaceholder)))
  root.querySelectorAll('[data-i18n-title]').forEach((el) => el.setAttribute('title', t(el.dataset.i18nTitle)))
  root.querySelectorAll('[data-i18n-aria-label]').forEach((el) => el.setAttribute('aria-label', t(el.dataset.i18nAriaLabel)))
}

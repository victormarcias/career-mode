import { settings } from './api.js'
import { escapeHtml } from './dom-utils.js'
import { t } from './i18n.js'

// The page is a stack of sections, each one entry in this list. To add a section,
// add an entry whose render(container) fills its card in.
const SECTIONS = [
  {
    id: 'env',
    title: 'settings.config.title',
    description: 'settings.config.description',
    render: renderEnvSection,
  },
]

// Escapes the text and turns what is between backticks (a filename or a command) into code.
export function codeHtml(text) {
  return escapeHtml(text).replace(/`([^`\n]+)`/g, `<code class="code">$1</code>`)
}

function spinnerHtml() {
  return '<div class="flex justify-center py-6"><div class="h-5 w-5 animate-spin rounded-full border-2 border-gray-700 border-t-gray-300"></div></div>'
}

// What to send for the form as it stands: only what changed. A secret left empty is kept as it is, and so is
// one the eye filled in and nobody edited (`original` is what the eye loaded); one the eye filled in and
// somebody cleared is removed. A plain value emptied goes back to its default. `state` is
// {NAME: {typed, original}}; a variable it doesn't mention is left alone.
export function envPayload(vars, state) {
  const values = {}
  for (const v of vars) {
    const s = state[v.name]
    if (!s) continue
    const typed = (s.typed ?? '').trim()
    if (v.secret) {
      if (typed && typed !== s.original) values[v.name] = typed
      else if (!typed && s.original !== undefined) values[v.name] = null
    } else if (typed !== (v.value ?? (v.choices ? v.default : null) ?? '')) {
      values[v.name] = typed || null
    }
  }
  return values
}

// What a field says about itself, shown from when it gets the focus until another field gets it (see .field-hint in style.css).
function hintText(v) {
  const parts = [t(`settings.var.${v.name}.description`, {}, v.description)]
  if (v.default) parts.push(t('settings.hint.default', { value: v.default }))
  if (v.restartRequired) parts.push(t('settings.hint.restart'))
  if (v.secret) parts.push(t('settings.hint.secret'))
  return parts.join(' ')
}

function hintHtml(id, text) {
  return `<div class="field-hint"><div class="field-hint-inner"><p id="${id}-hint" class="pt-2 text-xs text-gray-500">${codeHtml(text)}</p></div></div>`
}

// The settings that belong together share the start of their name (EMAIL_*, GOOGLE_*): the page draws a line only between those groups.
export function groupsHtml(vars) {
  const groups = []
  for (const v of vars) {
    const key = v.name.split('_')[0]
    const last = groups[groups.length - 1]
    if (last?.key === key) last.vars.push(v)
    else groups.push({ key, vars: [v] })
  }
  return groups.map((g) => `<div class="space-y-3 py-4 first:pt-0 [&>.field]:p-0">${g.vars.map(fieldHtml).join('')}</div>`).join('')
}

// The name of a setting, in white as code: the only title a field has.
function keyHtml(name, forId) {
  const code = `<code class="font-mono text-sm text-white">${name}</code>`
  return forId ? `<label for="${forId}" class="mb-1.5 block w-fit">${code}</label>` : `<p class="mb-1.5">${code}</p>`
}

export function fieldHtml(v) {
  const id = `env-${v.name}`
  const label = t(`settings.var.${v.name}.label`, {}, v.label)
  const input = v.choices
    ? `<select id="${id}" name="${v.name}" aria-label="${escapeHtml(label)}" aria-describedby="${id}-hint"
        class="select-chevron w-full appearance-none rounded-lg border border-gray-700 bg-gray-800 py-2 pl-3 pr-9 text-sm text-gray-100">
        ${v.choices.map((c) => `<option value="${c}"${c === (v.value ?? v.default) ? ' selected' : ''}>${escapeHtml(t(`settings.choice.${v.name}.${c}`, {}, c))}</option>`).join('')}
      </select>`
    : v.secret
    ? `<div class="relative">
        <input id="env-${v.name}" name="${v.name}" type="password" autocomplete="off" spellcheck="false" data-is-set="${v.isSet}" aria-label="${escapeHtml(label)}" aria-describedby="env-${v.name}-hint"
          placeholder="${v.isSet ? '•'.repeat(v.length || 8) : t('settings.notSet')}"
          class="w-full rounded-lg border border-gray-700 bg-gray-800 py-2 pl-3 pr-11 text-sm text-gray-100" />
        <button type="button" data-reveal="${v.name}" title="${t('settings.show')}" aria-label="${escapeHtml(t('settings.showLabel', { label }))}"
          class="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-lg text-gray-500 hover:text-gray-200">
          <svg data-icon="show" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="h-5 w-5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.04 12.32a1 1 0 0 1 0-.64C3.42 8.2 7.36 5 12 5s8.58 3.2 9.96 6.68a1 1 0 0 1 0 .64C20.58 15.8 16.64 19 12 19s-8.58-3.2-9.96-6.68Z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"/></svg><svg data-icon="hide" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="hidden h-5 w-5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.22A10.48 10.48 0 0 0 2.04 11.68a1 1 0 0 0 0 .64C3.42 15.8 7.36 19 12 19c1.99 0 3.84-.58 5.4-1.58M6.23 6.23A10.45 10.45 0 0 1 12 5c4.64 0 8.58 3.2 9.96 6.68a1 1 0 0 1 0 .64 10.5 10.5 0 0 1-4.07 4.97M6.23 6.23 3 3m3.23 3.23 3.65 3.65m7.89 7.89L21 21m-3.23-3.23-3.65-3.65m0 0a3 3 0 1 0-4.24-4.24m4.24 4.24L9.88 9.88"/></svg>
        </button>
      </div>`
    : `<input id="${id}" name="${v.name}" type="text" autocomplete="off" spellcheck="false"
        value="${escapeHtml(v.value ?? '')}" placeholder="${escapeHtml(v.default ?? '')}" aria-label="${escapeHtml(label)}" aria-describedby="${id}-hint"
        class="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100" />`
  return `
    <div class="field py-4 first:pt-0">
      ${keyHtml(v.name, id)}
      ${input}
      ${hintHtml(id, hintText(v))}
    </div>
  `
}

// The eye: shows what is in a secret's field, or hides it again. The first time, for a
// secret that is set and whose field is still empty, it asks the server for the real
// value and keeps it in `dataset.original`, so saving without editing sends nothing.
// Returns whether the field is now showing its text. If the server refuses, the field
// stays hidden and the error is thrown.
export async function toggleReveal(input, fetchSecret) {
  if (input.type === 'text') {
    input.type = 'password'
    return false
  }
  if (!input.value && input.dataset.isSet === 'true' && input.dataset.original === undefined) {
    const { value } = await fetchSecret(input.name)
    if (value) {
      input.value = value
      input.dataset.original = value
    }
  }
  input.type = 'text'
  return true
}

const MB = 1024 * 1024
const PHOTO_MAX_BYTES = 1 * MB

function sizeText(bytes) {
  return bytes >= MB ? `${(bytes / MB).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

// The last item of the list: the profile picture, a file in profile/ that is uploaded right away (no Save needed).
function pictureRowHtml() {
  return `
    <div class="field py-4">
      ${keyHtml('PROFILE_PICTURE_FILE')}
      <div data-picture></div>
      ${hintHtml('env-PROFILE_PICTURE_FILE', t('settings.picture.hint', { mb: PHOTO_MAX_BYTES / MB }))}
    </div>
  `
}

// The photo is the one file kept in profile/ (PROFILE_PICTURE_FILE): shown with its name and size, and replaced or removed right away.
function renderPhotoBlock(el, photo, message = null) {
  const preview = photo
    ? `<img src="/profile-files/photo?v=${encodeURIComponent(photo.updated)}" alt="" class="h-14 w-14 shrink-0 rounded-full border border-gray-700 object-cover" />`
    : '<span class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-gray-700 bg-gray-800 text-xl">👤</span>'
  const current = photo
    ? `<span class="text-gray-100">${escapeHtml(photo.name)}</span> <span class="text-gray-500">· ${sizeText(photo.size)}</span>`
    : `<span class="text-gray-500">${t('settings.picture.none')}</span>`
  el.innerHTML = `
    <div class="flex items-center gap-4">
      ${preview}
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm">${current}</p>
        <p class="photo-status min-h-[1rem] text-xs"></p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <input type="file" accept="image/png,image/jpeg" class="hidden" data-input />
        <button type="button" data-upload class="tab-pill">${photo ? t('settings.picture.replace') : t('settings.picture.upload')}</button>
        ${photo ? `<button type="button" data-remove class="tab-pill">${t('settings.picture.remove')}</button>` : ''}
      </div>
    </div>
  `
  const line = el.querySelector('.photo-status')
  const say = (tone, text) => {
    line.className = `photo-status min-h-[1rem] text-xs ${tone === 'error' ? 'text-red-400' : tone === 'success' ? 'text-green-400' : 'text-gray-500'}`
    line.innerHTML = codeHtml(text)
  }
  if (message) say(message.tone, message.text)

  const input = el.querySelector('[data-input]')
  el.querySelector('[data-upload]').addEventListener('click', () => input.click())
  input.addEventListener('change', async () => {
    const file = input.files[0]
    if (!file) return
    if (file.size > PHOTO_MAX_BYTES) return say('error', t('settings.picture.tooBig', { mb: PHOTO_MAX_BYTES / MB }))
    say('muted', t('settings.picture.uploading'))
    try {
      const saved = await settings.uploadPhoto(file)
      renderPhotoBlock(el, saved, { tone: 'success', text: t('settings.picture.saved') })
    } catch (err) {
      say('error', err.message)
    }
  })
  el.querySelector('[data-remove]')?.addEventListener('click', async () => {
    try {
      await settings.removePhoto()
      renderPhotoBlock(el, null, { tone: 'muted', text: t('settings.picture.removed') })
    } catch (err) {
      say('error', err.message)
    }
  })
}

// `notice` is shown under the form after it redraws: {kind: 'success' | 'error', text}.
async function renderEnvSection(container, notice = null) {
  container.innerHTML = spinnerHtml()
  let vars
  try {
    vars = await settings.env()
  } catch (err) {
    container.innerHTML = `<p class="text-sm text-red-400">${escapeHtml(err.message)}</p>`
    return
  }

  container.innerHTML = `
    <form autocomplete="off">
      <div class="divide-y divide-gray-800">${groupsHtml(vars)}${pictureRowHtml()}</div>
      <div class="flex items-center gap-3 border-t border-gray-800 pt-5">
        <button type="submit" class="shrink-0 whitespace-nowrap rounded-full bg-gray-100 px-5 py-2 text-sm font-medium text-gray-900 hover:bg-white disabled:opacity-50">${t('common.save')}</button>
        <span class="settings-status min-w-0 text-xs"></span>
      </div>
    </form>
  `
  const form = container.querySelector('form')
  const status = container.querySelector('.settings-status')
  settings.photo().then((photo) => renderPhotoBlock(container.querySelector('[data-picture]'), photo)).catch((err) => {
    container.querySelector('[data-picture]').innerHTML = `<p class="text-sm text-red-400">${escapeHtml(err.message)}</p>`
  })
  const say = (kind, text) => {
    status.className = `settings-status min-w-0 text-xs ${kind === 'error' ? 'text-red-400' : kind === 'success' ? 'text-green-400' : 'text-gray-500'}`
    status.innerHTML = codeHtml(text)
  }
  if (notice) say(notice.kind, notice.text)

  form.addEventListener('focusin', (e) => {
    const field = e.target.closest('.field')
    if (!field) return
    form.querySelectorAll('.field.is-open').forEach((other) => other !== field && other.classList.remove('is-open'))
    field.classList.add('is-open')
  })

  form.querySelectorAll('[data-reveal]').forEach((button) => {
    button.addEventListener('click', async () => {
      const input = form.elements[button.dataset.reveal]
      button.disabled = true
      try {
        const showing = await toggleReveal(input, settings.reveal)
        button.querySelector('[data-icon="show"]').classList.toggle('hidden', showing)
        button.querySelector('[data-icon="hide"]').classList.toggle('hidden', !showing)
        button.title = showing ? t('settings.hide') : t('settings.show')
      } catch (err) {
        say('error', err.message)
      } finally {
        button.disabled = false
      }
    })
  })

  form.addEventListener('submit', async (e) => {
    e.preventDefault()
    const state = Object.fromEntries(
      vars.map((v) => [
        v.name,
        { typed: form.elements[v.name].value, original: form.elements[v.name].dataset.original },
      ]),
    )
    const values = envPayload(vars, state)
    if (!Object.keys(values).length) return say('muted', t('settings.nothingToChange'))

    const submit = form.querySelector('button[type="submit"]')
    submit.disabled = true
    say('muted', t('settings.saving'))
    try {
      await settings.saveEnv(values)
      if ('APP_LANGUAGE' in values) return location.reload() // the page is drawn in the new language
      const restart = vars.some((v) => v.restartRequired && v.name in values)
      await renderEnvSection(container, {
        kind: 'success',
        text: restart ? t('settings.savedRestart') : t('settings.saved'),
      })
    } catch (err) {
      submit.disabled = false
      say('error', err.message)
    }
  })
}

export function renderSettings() {
  const page = document.getElementById('settings-content')
  page.innerHTML = SECTIONS.map(
    (s) => `
      <section class="rounded-2xl border border-gray-800 bg-gray-900 p-6" data-section="${s.id}">
        <h2 class="text-base font-medium text-gray-100">${escapeHtml(t(s.title))}</h2>
        <p class="mb-5 mt-1 text-xs text-gray-500">${codeHtml(t(s.description))}</p>
        <div class="settings-body"></div>
      </section>
    `,
  ).join('')
  SECTIONS.forEach((s) => s.render(page.querySelector(`[data-section="${s.id}"] .settings-body`)))
}

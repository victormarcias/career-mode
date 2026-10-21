import { t } from './i18n.js'

// Agency/client ids are the slugified name. The server builds them the same way
// (server/app/crud.py), so this is only for matching a typed name against an id.
function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

// Finds the existing agency/client a typed name refers to: by name (ignoring case
// and surrounding spaces) first, then by the id slugify() would give it. Looking
// only at the slug misses a company whose id was set some other way (e.g. "cwssg" for
// "CW Strategic Solutions Group"), and creating a second one for it. `items` are
// {id, name} pairs. Returns the one to reuse, or what a new one would be.
export function resolveCompany(items, name) {
  const wanted = name.trim()
  const found =
    items.find((i) => (i.name ?? '').trim().toLowerCase() === wanted.toLowerCase()) ?? items.find((i) => i.id === slugify(wanted))
  return found ? { id: found.id, name: found.name ?? wanted, isNew: false } : { id: slugify(wanted), name: wanted, isNew: true }
}

// A form takes one company: a name and a tag, Agency or Client. `agencies` and `clients` are {id, name} lists.
// The company a typed name already is, in each list: `{agency, client}`, each an existing {id, name} or null.
export function companyMatches(agencies, clients, name) {
  const wanted = (name ?? '').trim()
  const find = (items) => {
    const found = wanted ? resolveCompany(items, wanted) : null
    return found && !found.isNew ? found : null
  }
  return { agency: find(agencies), client: find(clients) }
}

// The tag a typed name goes by: the one it already has when it exists as only one of them, else `current`.
// Typing the name of an existing company is picking it, so its tag follows.
export function kindFor(agencies, clients, name, current) {
  const { agency, client } = companyMatches(agencies, clients, name)
  if (agency && !client) return 'agency'
  if (client && !agency) return 'client'
  return current
}

// The tag a name has when it exists only with the other one than `kind`, else null: saving it would make a
// second company with the same name.
export function kindConflict(agencies, clients, name, kind) {
  const matches = companyMatches(agencies, clients, name)
  const other = kind === 'agency' ? 'client' : 'agency'
  return !matches[kind] && matches[other] ? other : null
}

// The sentence that says a name is already the other kind.
export function kindConflictText(name, existing) {
  return t(existing === 'agency' ? 'hint.isAgency' : 'hint.isClient', { name: name.trim() })
}

// The agency and client names a company with its tag stands for (the way the API and the events have them): an
// agency is the agency alone, a client has its agency `via` when it comes through one.
export function companyNames({ name, kind, via }) {
  return kind === 'client' ? { agency: (via ?? '').trim(), client: (name ?? '').trim() } : { agency: (name ?? '').trim(), client: '' }
}

// The other way round: the company, tag and via agency of an event's agency and client names.
export function companyFromNames(agencyName, clientName) {
  return clientName ? { name: clientName, kind: 'client', via: agencyName ?? '' } : { name: agencyName ?? '', kind: 'agency', via: '' }
}

// What a form says about the company it is about to save: which names the app doesn't have yet and will
// create, or that the name is already the other tag. Empty when every name is already there.
export function companyHint(agencies, clients, name, kind, via = '') {
  const company = (name ?? '').trim()
  const conflict = kindConflict(agencies, clients, company, kind)
  if (conflict) return kindConflictText(company, conflict)
  const agency = kind === 'client' ? (via ?? '').trim() : company
  const newCompany = company && !companyMatches(agencies, clients, company)[kind]
  const newAgency = kind === 'client' && agency && !companyMatches(agencies, clients, agency).agency
  if (newCompany && newAgency) return t('hint.both', { agency, client: company })
  if (newCompany) return t(kind === 'agency' ? 'hint.agency' : 'hint.client', { name: company })
  if (newAgency) return t('hint.agency', { name: agency })
  return ''
}

const NOTICE_MS = 200 // as long as the fold in style.css (.notice)

// Shows a notice line (a hint, an error, a status) with `text`, or folds it away when `text` is empty. The line
// grows and shrinks vertically (see .notice in style.css) instead of popping in; the old text stays while it
// folds, and is cleared once it is gone.
export function setNotice(el, text) {
  clearTimeout(el._noticeTimer)
  if (text) {
    el.textContent = text
    el.classList.add('is-open')
  } else {
    el.classList.remove('is-open')
    el._noticeTimer = setTimeout(() => {
      el.textContent = ''
    }, NOTICE_MS)
  }
}

// A queued (`pending`) link has no company yet (its companyLabel is "—"), so the start of the link is its
// name: without the protocol or "www.", cut to a few characters.
const PENDING_LABEL_CHARS = 15

export function pendingLabel(app) {
  const link = (app.jdUrl ?? '').replace(/^https?:\/\/(www\.)?/i, '')
  if (!link) return app.companyLabel ?? ''
  return link.length > PENDING_LABEL_CHARS ? link.slice(0, PENDING_LABEL_CHARS) + '...' : link
}

export function escapeHtml(text) {
  return (text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// A title that starts with an emoji ("🤝 Platform Reachout Message") is shown with the emoji apart, as a company
// card shows its building.
function splitTitle(title) {
  const match = title.match(/^(\p{Extended_Pictographic}\S*)\s+(.+)$/u)
  return match ? { emoji: match[1], name: match[2] } : { emoji: '', name: title }
}

// One collapsible card, built like a company's card in Companies: the emoji and the title in the header, `body`
// (html) inside. Open it with `open`; wireAccordion makes the headers work once the page is in place.
export function cardHtml({ title, open = false, body }) {
  const { emoji, name } = splitTitle(title)
  return `
  <div class="capsule" data-open="${open}">
    <button type="button" class="capsule-summary" aria-expanded="${open}">
      <div class="flex w-full items-center gap-2">${emoji ? `
        <span>${escapeHtml(emoji)}</span>` : ''}
        <span class="font-medium text-gray-100">${escapeHtml(name)}</span>
      </div>
    </button>
    <div class="capsule-body-wrap">
      <div class="capsule-body">${body}
      </div>
    </div>
  </div>`
}

// The notice shown above a page while it still holds the example's content, with the prompt (or command) to copy.
export function bannerHtml({ title, text, prompt }) {
  return `<div class="mb-4">
    <div class="rounded-xl border border-amber-800/60 bg-amber-950/30 p-4 text-sm text-amber-200">
      <p class="font-medium">${escapeHtml(title)}</p>
      <p class="mt-1">${escapeHtml(text)}</p>
      <pre class="outreach-box mt-2"><code>${escapeHtml(prompt)}</code></pre>
    </div>
  </div>`
}

// Markdown-style `[text](url)`, or a bare `https://...` pasted straight from a
// recruiter email/ATS notification — both become clickable. One pass so a
// markdown link's own URL is never re-matched as a second, bare link.
const LINK_PATTERN = /\[([^\]]+)\]\(([^)]+)\)|(https?:\/\/[^\s<]+)/g

export function renderNotes(text) {
  const escaped = (text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/&lt;br&gt;/g, '<br>')

  return escaped.replace(LINK_PATTERN, (match, mdText, mdUrl, bareUrl) => {
    // Don't swallow sentence punctuation right after a bare URL (a closing
    // period, comma, or parenthesis) into the link itself.
    const trailing = bareUrl ? bareUrl.match(/[.,;:!?)]+$/)?.[0] ?? '' : ''
    const url = trailing ? bareUrl.slice(0, -trailing.length) : (mdUrl ?? bareUrl)
    const label = mdText ?? url
    return `<a href="${url}" target="_blank" rel="noreferrer" class="text-blue-400 underline hover:text-blue-300">${label}</a>${trailing}`
  })
}

export function addCopyButtons(container) {
  container.querySelectorAll('pre').forEach((pre) => {
    const text = pre.textContent
    const btn = document.createElement('button')
    btn.type = 'button'
    btn.className = 'copy-btn'
    btn.textContent = t('common.copy')
    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(text)
      btn.textContent = t('common.copied')
      setTimeout(() => (btn.textContent = t('common.copy')), 1200)
    })
    pre.appendChild(btn)
  })
}

// Same left/right slide used for calendar week navigation, reusable for any
// container that needs a "moved to the next/previous section" transition.
// `container` must have the `slide-transition` class (see style.css).
export function slideTransition(container, direction, renderFn, duration = 180) {
  container.classList.add(direction === 'left' ? 'slide-out-left' : 'slide-out-right')
  setTimeout(() => {
    container.classList.remove('slide-out-left', 'slide-out-right')
    container.classList.add(direction === 'left' ? 'slide-in-prepare-left' : 'slide-in-prepare-right')
    renderFn()
    void container.offsetWidth // force reflow so the next class change transitions
    container.classList.remove('slide-in-prepare-left', 'slide-in-prepare-right')
  }, duration)
}

// Fade out/in only, no horizontal movement — for a content refresh that isn't
// "moved to a different section" (e.g. a filter changing), unlike slideTransition.
export function fadeTransition(container, renderFn, duration = 180) {
  container.classList.add('fade-out-only')
  setTimeout(() => {
    renderFn()
    container.classList.remove('fade-out-only')
  }, duration)
}

// Wires up all `.capsule` elements within `container` as an accordion: opening
// one closes any other that's open. See the `.capsule*` rules in style.css.
export function wireAccordion(container) {
  const summaries = container.querySelectorAll('.capsule:not(.capsule-static) .capsule-summary')
  summaries.forEach((btn) => {
    btn.addEventListener('click', () => {
      const capsule = btn.closest('.capsule')
      const open = capsule.dataset.open !== 'true'
      if (open) {
        summaries.forEach((otherBtn) => {
          const otherCapsule = otherBtn.closest('.capsule')
          if (otherCapsule !== capsule) {
            otherCapsule.dataset.open = 'false'
            otherBtn.setAttribute('aria-expanded', 'false')
          }
        })
      }
      capsule.dataset.open = String(open)
      btn.setAttribute('aria-expanded', String(open))
    })
  })
}

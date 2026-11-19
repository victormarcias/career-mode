import { escapeHtml } from './dom-utils.js'

// The company suggestions of every field marked data-suggest="company" (agencies and clients) or "agency": a list
// under the field that opens as soon as you type and narrows with each letter, to the names that contain what the
// field holds. Pick one with a click, or with the arrows and Enter; Escape closes it. The browser's own <datalist>
// was dropped: Chrome closes it whenever its options change while typing.
const box = document.createElement('ul')
box.className = 'fixed z-[60] hidden max-h-64 overflow-y-auto rounded-lg border border-gray-700 bg-gray-900 py-1 text-sm shadow-xl'
let field = null
let active = -1

function close() {
  box.classList.add('hidden')
  field = null
}

function highlight(index) {
  const items = box.children
  active = Math.max(-1, Math.min(index, items.length - 1))
  Array.from(items).forEach((li, i) => li.classList.toggle('bg-gray-800', i === active))
  items[active]?.scrollIntoView({ block: 'nearest' })
}

function pick(li) {
  const target = field
  target.value = li.dataset.value
  close()
  target.dispatchEvent(new Event('input', { bubbles: true })) // so each form reacts as if it had been typed
  target.dispatchEvent(new Event('change', { bubbles: true }))
}

// `suggestions(kind)` gives the [{ name, tag }] a field of that kind offers.
export function initSuggest(suggestions) {
  document.body.append(box)
  const open = (e) => {
    if (!e.target.dataset?.suggest) return
    field = e.target
    const query = field.value.trim().toLowerCase()
    const items = suggestions(field.dataset.suggest).filter((s) => s.name.toLowerCase().includes(query))
    // Nothing to offer, or only the name already there: no list.
    if (!items.length || (items.length === 1 && items[0].name === field.value.trim())) return close()
    box.innerHTML = items
      .map((s) => `<li data-value="${escapeHtml(s.name)}" class="flex cursor-pointer justify-between gap-3 px-3 py-1.5 text-gray-100 hover:bg-gray-800"><span class="min-w-0">${escapeHtml(s.name)}</span>${s.tag ? `<span class="shrink-0 text-gray-500">${escapeHtml(s.tag)}</span>` : ''}</li>`)
      .join('')
    const rect = field.getBoundingClientRect()
    Object.assign(box.style, { left: `${rect.left}px`, top: `${rect.bottom + 4}px`, width: `${rect.width}px` })
    box.classList.remove('hidden')
    highlight(-1)
  }
  document.addEventListener('input', open)
  document.addEventListener('focusin', open)
  document.addEventListener('focusout', (e) => { if (e.target === field) close() })
  // A click on a name picks it before the field loses the focus.
  box.addEventListener('mousedown', (e) => {
    const li = e.target.closest('li')
    if (!li) return
    e.preventDefault()
    pick(li)
  })
  document.addEventListener('keydown', (e) => {
    if (!field || e.target !== field || box.classList.contains('hidden')) return
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      highlight(active + (e.key === 'ArrowDown' ? 1 : -1))
    } else if (e.key === 'Enter' && active >= 0) {
      e.preventDefault()
      pick(box.children[active])
    } else if (e.key === 'Escape') {
      e.stopPropagation() // closes the list, not the form
      close()
    }
  }, true)
  // The list is placed under the field once: a scroll would leave it behind, so it closes.
  window.addEventListener('scroll', (e) => { if (e.target !== box) close() }, true)
}

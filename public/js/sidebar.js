import { t } from './i18n.js'

// The sidebar shows only its icons when the content to its right stops fitting (the Calendar's header needs about 1,200 px
// with the full sidebar, and it is the widest page), or when the toggle at the top of it says so.
export const AUTO_COLLAPSE_BELOW = 1240
const KEY = 'sidebar-collapsed'

// `choice` is what the person picked with the toggle (true: icons only, false: full), or null when they have not: then the
// window decides.
export function isCollapsed(choice, width) {
  return choice ?? width < AUTO_COLLAPSE_BELOW
}

function readChoice() {
  try {
    const saved = localStorage.getItem(KEY)
    return saved === null ? null : saved === '1'
  } catch {
    return null
  }
}

function saveChoice(choice) {
  try {
    if (choice === null) localStorage.removeItem(KEY)
    else localStorage.setItem(KEY, choice ? '1' : '0')
  } catch {
    // no storage: the choice lasts until the page is closed
  }
}

export function initSidebar() {
  const nav = document.getElementById('sidebar')
  const toggle = document.getElementById('sidebar-toggle')
  let choice = readChoice()

  const apply = () => {
    const collapsed = isCollapsed(choice, window.innerWidth)
    nav.classList.toggle('is-collapsed', collapsed)
    toggle.setAttribute('aria-expanded', String(!collapsed))
    const label = t(collapsed ? 'sidebar.expand' : 'sidebar.collapse')
    toggle.title = label
    toggle.setAttribute('aria-label', label)
    // with the names hidden, a tooltip says what each icon is
    nav.querySelectorAll('.side-item').forEach((item) => {
      if (collapsed) item.title = item.querySelector('.nav-label').textContent
      else item.removeAttribute('title')
    })
  }

  toggle.addEventListener('click', () => {
    choice = !isCollapsed(choice, window.innerWidth)
    saveChoice(choice)
    apply()
  })
  // Crossing the point where the content stops fitting hands the decision back to the window.
  window.matchMedia(`(max-width: ${AUTO_COLLAPSE_BELOW - 1}px)`).addEventListener('change', () => {
    choice = null
    saveChoice(null)
    apply()
  })

  apply()
  requestAnimationFrame(() => nav.classList.add('has-transition'))  // not on load: it would slide in from the full width
}

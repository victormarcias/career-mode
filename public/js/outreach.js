import { addCopyButtons, bannerHtml, slideTransition, wireAccordion } from './dom-utils.js'
import { outreachHtml } from './outreach-parser.js'
import { t } from './i18n.js'

// An email address means email; any other valid link is a web form, for now. It is only a guess from what was
// typed: a queued link is a stand-in, and /apply-pending reads the JD Post and corrects it. Shared with main.js
// so the "+ New event" form can deduce the same channel from its JD link field.
export function detectApplyType(value) {
  if (!value) return null
  if (value.includes('@')) return 'email_apply'
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol) ? 'web_form' : null
  } catch {
    return null
  }
}

const TABS = [
  { id: 'messages', label: 'outreach.tabMessages' },
  { id: 'questions', label: 'outreach.tabQuestions' },
]

let currentTab = null

// Each tab's content is a plain static HTML file — no database data or user
// input involved, so it's just fetched and dropped in, not built up from JS.
// Fetched once per tab, then cached.
// The Messages tab is the user's own outreach.md, drawn by outreachHtml; Questions is a ready-made page.
const TAB_FILES = {
  messages: 'outreach.md',
  questions: 'navigation/questions.html',
}
const contentCache = new Map()
// The tabs whose content is still the example's (the server says so in a header): see exampleBannerHtml.
const exampleTabs = new Set()

async function loadTabContent(tab) {
  if (contentCache.has(tab)) return
  const res = await fetch(TAB_FILES[tab])
  if (res.headers.get('X-Profile-Example') === 'true') exampleTabs.add(tab)
  const text = await res.text()
  contentCache.set(tab, tab === 'messages' ? outreachHtml(text) : text)
}

const EXAMPLE_PROMPT = `Fill profile/outreach.md from my messages document:
<DOCUMENT LINK>
Follow profile/outreach.example.md: same titles, same structure.
Copy each text word for word. Show me the result before saving.`

// Until the user writes their own, the messages are only titles with a placeholder where each text goes, and the
// skills use them in real applications. Writing them is optional, so this only says how: it is shown above the
// cards, with the prompt to hand an AI.
function exampleBannerHtml() {
  return bannerHtml({
    title: t('outreach.bannerTitle'),
    text: t('outreach.bannerText'),
    prompt: EXAMPLE_PROMPT,
  })
}

function wireInteractivity(content) {
  addCopyButtons(content)
  wireAccordion(content)
}

function renderTabBar(activeTab) {
  const el = document.getElementById('outreach-tabs')
  el.innerHTML = TABS.map(
    (tab) => `<button type="button" class="tab-pill${tab.id === activeTab ? ' active' : ''}" data-tab="${tab.id}">${t(tab.label)}</button>`,
  ).join('')
  el.querySelectorAll('.tab-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      location.hash = `outreach/${btn.dataset.tab}`
    })
  })
}

export async function renderOutreach(tab) {
  if (!TABS.some((t) => t.id === tab)) tab = 'messages'
  await loadTabContent(tab)

  renderTabBar(tab)
  const content = document.getElementById('outreach-content')

  if (currentTab === tab) return

  const renderContent = () => {
    content.innerHTML = (exampleTabs.has(tab) ? exampleBannerHtml() : '') + contentCache.get(tab)
    wireInteractivity(content)
  }

  if (currentTab === null) {
    renderContent()
  } else {
    const oldIndex = TABS.findIndex((t) => t.id === currentTab)
    const newIndex = TABS.findIndex((t) => t.id === tab)
    slideTransition(content, newIndex > oldIndex ? 'left' : 'right', renderContent)
  }
  currentTab = tab
}

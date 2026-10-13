import { addCopyButtons, bannerHtml, cardHtml, escapeHtml, wireAccordion } from './dom-utils.js'
import { markdownHtml, markdownSections } from './markdown.js'
import { t } from './i18n.js'

const EXAMPLE_COMMAND = '/read-cv <path or link to your CV PDF>'

// Until the user fills their profile it is the example's, an invented person, and every skill would fill forms
// with it. Filling it is optional, so this only says how.
function profileBannerHtml() {
  return bannerHtml({
    title: t('profile.bannerTitle'),
    text: t('profile.bannerText'),
    prompt: EXAMPLE_COMMAND,
  })
}

// The profile as cards, one per section, in the same style as Companies and the Messages tab. The first is open.
function profileHtml(markdown, isExample = false) {
  const sections = markdownSections(markdown)
  const cards = sections.map((s, i) => cardHtml({ title: s.title, open: i === 0, body: markdownHtml(s.body) })).join('\n')
  return `${isExample ? profileBannerHtml() : ''}<div class="space-y-3">${cards || `<p class="text-sm text-gray-500">${t('profile.noSections')}</p>`}
</div>`
}

export async function renderProfile() {
  const content = document.getElementById('profile-content')
  let html
  try {
    const res = await fetch('profile.md')
    if (!res.ok) throw new Error(t('profile.errServer', { status: res.status }))
    html = profileHtml(await res.text(), res.headers.get('X-Profile-Example') === 'true')
  } catch (err) {
    content.innerHTML = `<p class="text-sm text-red-400">${t('profile.errLoad', { message: escapeHtml(err.message) })}</p>`
    return
  }
  content.innerHTML = html
  addCopyButtons(content)
  wireAccordion(content)
}

import { t } from './i18n.js'
import { cardHtml, escapeHtml } from './dom-utils.js'

// profile/outreach.md is what a document exports as markdown: a title and an intro, then for each message a `##`
// heading and, for each language, a `###` heading followed by the text in a code block (so its line breaks stay
// exactly as written). Anything else in the file, the title and the intro included, is for whoever edits it and
// is not shown.
function parseOutreach(markdown) {
  const messages = []
  let message = null
  let language = null
  let fence = null // the lines of the code block being read
  for (const line of markdown.replace(/\r\n/g, '\n').split('\n')) {
    const isFence = line.trim().startsWith('```')
    if (fence) {
      if (isFence) {
        if (message && language) message.texts.push({ language, text: fence.join('\n') })
        fence = null
      } else {
        fence.push(line)
      }
    } else if (isFence) {
      fence = []
    } else if (line.startsWith('## ')) {
      message = { title: line.slice(3).trim(), texts: [] }
      messages.push(message)
      language = null
    } else if (line.startsWith('### ') && message) {
      language = line.slice(4).trim()
    }
  }
  return messages
}

// The Messages tab: one collapsible card per message (the first open), with its texts in the box of a company's
// Timeline entry and a Copy button on each (added by addCopyButtons, once the page is in place).
export function outreachHtml(markdown) {
  const messages = parseOutreach(markdown)
  const cards = messages
    .map((m, i) => {
      const body = m.texts
        .map(
          (text) => `
        <div class="mb-3 last:mb-0">
          <p class="mb-1 text-xs text-gray-500">${escapeHtml(text.language)} · ${t('outreach.characters', { count: [...text.text].length })}</p>
          <pre class="outreach-box"><code>${escapeHtml(text.text)}</code></pre>
        </div>`,
        )
        .join('')
      return cardHtml({ title: m.title, open: i === 0, body })
    })
    .join('\n')
  return `<div>
<p class="outreach-prose">${messages.length ? t('outreach.intro') : t('outreach.none')}</p>
<div class="space-y-3">${cards}
</div>
</div>`
}

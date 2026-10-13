import { escapeHtml } from './dom-utils.js'

// A small markdown to html for the user's own files (the profile). It knows what those files use and nothing
// else: ### headings, paragraphs, nested bullet and numbered lists (a paragraph under an item belongs to it),
// code blocks, and in a line `code`, **bold**, *italic* and [text](https://link). Everything is escaped first.
const LINK_CLASS = 'text-blue-400 underline hover:text-blue-300'

function inlineHtml(text) {
  const spans = []
  // `code` is set aside first, so what is inside it is never read as bold, italic or a link
  const held = escapeHtml(text).replace(/`([^`]+)`/g, (_, code) => {
    spans.push(`<code class="code">${code}</code>`)
    return `\u0000${spans.length - 1}\u0000`
  })
  return held
    .replace(/\[([^\]]+)\]\(((?:https?:\/\/|mailto:)[^)\s"]+)\)/g, `<a href="$2" target="_blank" rel="noreferrer" class="${LINK_CLASS}">$1</a>`)
    .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-100">$1</strong>')
    .replace(/(^|[\s(])\*([^*\s][^*]*?)\*(?=$|[\s).,;:!?])/g, '$1<em>$2</em>')
    .replace(/\u0000(\d+)\u0000/g, (_, i) => spans[Number(i)])
}

const MARKER = /^(\s*)([-*]|\d+\.)\s+(.*)$/
const indentOf = (line) => line.match(/^ */)[0].length

// Reads the list that starts at lines[i] (its items are at that line's indent). Returns [html, next line].
function listHtml(lines, start) {
  const base = indentOf(lines[start])
  const ordered = /\d+\./.test(lines[start].match(MARKER)[2])
  const items = []
  let i = start
  while (i < lines.length) {
    const marker = lines[i].match(MARKER)
    if (!marker || indentOf(lines[i]) !== base) break
    const item = { text: marker[3], children: [] }
    const content = base + marker[2].length + 1 // where this item's text begins: what is indented that far belongs to it
    i += 1
    while (i < lines.length) {
      let j = i
      while (j < lines.length && !lines[j].trim()) j += 1 // blank lines inside an item
      if (j >= lines.length || indentOf(lines[j]) < Math.min(content, base + 2)) break
      const child = lines[j].match(MARKER)
      if (child) {
        const [html, next] = listHtml(lines, j)
        item.children.push(html)
        i = next
      } else {
        const text = []
        while (j < lines.length && lines[j].trim() && !MARKER.test(lines[j]) && indentOf(lines[j]) >= base + 2) text.push(lines[j++].trim())
        item.children.push(`<p class="mt-2">${inlineHtml(text.join(' '))}</p>`)
        i = j
      }
    }
    items.push(item)
  }
  const tag = ordered ? 'ol' : 'ul'
  const style = ordered ? 'list-decimal' : 'list-disc'
  const html = `<${tag} class="${style} space-y-1 pl-5 text-sm text-gray-300">${items
    .map((it) => `<li>${inlineHtml(it.text)}${it.children.join('')}</li>`)
    .join('')}</${tag}>`
  return [html, i]
}

export function markdownHtml(markdown) {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  const out = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) {
      i += 1
    } else if (line.trim().startsWith('```')) {
      const code = []
      i += 1
      while (i < lines.length && !lines[i].trim().startsWith('```')) code.push(lines[i++])
      i += 1
      out.push(`<pre class="outreach-box mb-3"><code>${escapeHtml(code.join('\n'))}</code></pre>`)
    } else if (/^#{1,6}\s/.test(line)) {
      out.push(`<h3 class="mb-2 mt-4 text-sm font-medium text-gray-400">${inlineHtml(line.replace(/^#{1,6}\s+/, ''))}</h3>`)
      i += 1
    } else if (MARKER.test(line)) {
      const [html, next] = listHtml(lines, i)
      out.push(html.replace('<ul class="', '<ul class="mb-3 ').replace('<ol class="', '<ol class="mb-3 '))
      i = next
    } else {
      const text = []
      while (i < lines.length && lines[i].trim() && !lines[i].trim().startsWith('```') && !/^#{1,6}\s/.test(lines[i]) && !MARKER.test(lines[i])) text.push(lines[i++].trim())
      out.push(`<p class="mb-3 text-sm text-gray-300">${inlineHtml(text.join(' '))}</p>`)
    }
  }
  return out.join('\n')
}

// The sections of a profile file: every `## ` heading with the markdown under it (up to the next one). The title
// and the intro above the first section are for whoever edits the file, and are not shown.
export function markdownSections(markdown) {
  const sections = []
  let current = null
  let fenced = false
  for (const line of markdown.replace(/\r\n/g, '\n').split('\n')) {
    if (line.trim().startsWith('```')) fenced = !fenced
    if (!fenced && line.startsWith('## ')) {
      current = { title: line.slice(3).trim(), lines: [] }
      sections.push(current)
    } else if (current) {
      current.lines.push(line)
    }
  }
  return sections.map((s) => ({ title: s.title, body: s.lines.join('\n').trim() }))
}

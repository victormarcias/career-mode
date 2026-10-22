import { t } from './i18n.js'

// Every event type. The server (server/app/models.py) has the same list: change the two
// together. The Update/Edit event form does not offer
// `application`, `passive_message` or `archive` (see LOCKED_TYPES in main.js): they are logged with
// "+ Application" and the Archive buttons.
export const EVENT_TYPES = [
  'application',
  'passive_message',
  'note',
  'tech_filter',
  'hr_intro',
  'tech_interview',
  'culture_interview',
  'on_hold',
  'offer',
  'rejection',
  'red_flag',
  'archive',
]

// A company's status (derived from its latest event) and the Timeline sort both need to know
// which events end a process (archive the company, win a same-date tie)
// versus which ones don't.
const CLOSING_EVENTS = ['rejection', 'red_flag', 'on_hold', 'offer', 'archive']
export function isClosingEvent(event) {
  return CLOSING_EVENTS.includes(event)
}

const EVENT_EMOJIS = {
  pending: '⏳',
  application: '📝',
  passive_message: '📩',
  note: '🗒️',
  tech_filter: '🧪',
  hr_intro: '📞',
  tech_interview: '💻',
  culture_interview: '👥',
  on_hold: '⏸️',
  offer: '🎉',
  rejection: '❌',
  red_flag: '🚩',
  archive: '📦',
}

// {emoji, label} per type. The label is read when it is used, so it is in the language of the page.
export const EVENT_LABELS = Object.fromEntries(
  Object.entries(EVENT_EMOJIS).map(([type, emoji]) => [
    type,
    {
      emoji,
      get label() {
        return t(`events.${type}`)
      },
    },
  ]),
)

// Google-Calendar-style pill colors per event type (light bg + darkest possible text for legibility).
export const EVENT_COLORS = {
  pending: 'bg-cyan-100 text-cyan-950',
  application: 'bg-blue-100 text-blue-950',
  passive_message: 'bg-teal-100 text-teal-950',
  note: 'bg-yellow-100 text-yellow-950',
  // Technical/coding-evaluation events get a Matrix-console look (black bg, green text) instead of a
  // pastel — makes them pop out at a glance among the calendar's lighter pills. The black has to be
  // darker than the day column (bg-gray-900), or the pill disappears into it.
  tech_filter: 'bg-black text-green-400',
  hr_intro: 'bg-green-100 text-green-950',
  tech_interview: 'bg-black text-green-400',
  culture_interview: 'bg-violet-100 text-violet-950',
  on_hold: 'bg-amber-100 text-amber-950',
  offer: 'bg-emerald-100 text-emerald-950',
  rejection: 'bg-red-100 text-red-950',
  red_flag: 'bg-orange-100 text-orange-950',
  archive: 'bg-slate-200 text-slate-900',
}

// What every pill turns into while its company's other pills in the week are highlighted: one dark gray, so
// the week doesn't light up in as many colors as there are event types.
export const EVENT_COLOR_HIGHLIGHT = 'bg-gray-700 text-white'

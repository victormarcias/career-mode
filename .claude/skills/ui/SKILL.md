---
name: ui
description: Make a small change to the look of the career-mode app — a color, an emoji, a label, spacing, an icon, a text — in `public/` (HTML, Tailwind classes, CSS, the locales). Use whenever the user invokes /ui with the change they want, often with a screenshot of the part to change. Not for new features, the server or the data.
model: haiku
---

# Small UI change

The user says what to change, often with a screenshot. Make that change and
nothing else, quickly.

## Where things are

-  `public/index.html`: the page. Tailwind comes from its CDN, so any Tailwind
  class works without a build.
- `public/style.css`: the few styles that aren't Tailwind classes.
-  `public/js/*.js`: each tab's code. The event types' emojis (`EVENT_LABELS`)
  and colors (`EVENT_COLORS`) are in `public/js/events.js`; the companies list
  has its own status colors in `public/js/companies.js`.
- `public/locales/en.json` and `es.json`: every text the page shows.

Find the spot with `grep` on the text, class or emoji seen in the screenshot,
and look at its neighbors: when the same thing shows in more than one place (an
event's color, an emoji), change it everywhere it shows.

## Rules

-  A text the page shows is never written in a `.js` file or in `index.html`: it
  is a key in **both** `en.json` and `es.json`, with the same `{placeholders}`.
  Changing a text means changing it in both languages.
-  Keep it readable: text and emoji must keep good contrast on their background,
  and two kinds of entries must not end up looking alike (check the colors next
  to it in the same list, like `EVENT_COLORS`). If the change asked for would
  break that, make it and pick the closest choice that keeps it distinct, saying
  why.
-  A non-obvious choice (why this color, why this emoji) gets a one-line comment
  above it.
-  If `public/js/events.js` changes, run `node --test tests/js/`. Nothing else
  needs testing; the server doesn't need a restart (`public/` is served as it
  is), the user reloads the page.
- Don't commit: the user reads the diff and runs `/commit`.
-  If the change turns out not to be small (new behavior, the server, the data),
  stop and say so instead of doing it here.

## Answer

One or two sentences: what changed, in which file and line, any choice made
beyond the literal ask and why, and "reload the page to see it". Say plainly
that it wasn't looked at in the browser.

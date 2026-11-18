# ui

Small changes to the look of the app: a color, an emoji, a label, spacing, a
text. Run `/ui <what to change>`, usually with a screenshot of the part to
change. It finds the spot in `public/`, makes the change everywhere the same
thing shows, keeps the texts in both languages and the colors distinct and
readable, and tells you to reload the page. It runs on Haiku, since these
changes don't need a bigger model, and never commits. Anything bigger than a
small change it hands back. Instructions: [SKILL.md](SKILL.md).

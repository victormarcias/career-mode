# read-cv

Reads the user's CV (a PDF file or a link to one) and fills the CV-derived parts of `profile/profile.md`.

- **From the CV, every run:** education, the total years of experience as the CV states them, and every role with its dates, its technologies from its own "Tech:" line and its bullets word for word.
- **From the CV, first fill only:** name, location, time zone, citizenship, contact details and links, languages, a draft bio and the years per technology (calculated from the roles' dates). On a re-run the years are only compared with the user's own list: it says what differs and asks before changing anything.
- **Not from the CV:** the user's own decisions (priorities, preferences, salary range, expertise levels, birthdate, and, optionally, rules for presenting them). It asks for the ones still missing in one numbered message (any of it can be skipped for now: a skipped field is written as `(not set)`, never as the example's value) (contact, personal, setup for Claude, roles, stack, work preferences, self-assessment, portals, rules, and any gap in the CV itself), skips what is already set, never offers the example person's values as defaults, and never changes them on a re-run.
- **Safe by construction:** shows a before/after and waits for the OK, backs up the current profile in `profile/backups/`, and writes only `profile/profile.md`. A downloaded CV goes to a temporary directory outside the repo.
- **Use it:** `/read-cv <path or link to the PDF>`, the first time and whenever the CV changes. With no argument it reads the CV file of the `CV_PDF_PATH` setting. `profile/README.md` explains the rest of the profile.

Instructions: [SKILL.md](SKILL.md).

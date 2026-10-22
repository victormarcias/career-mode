# career-mode — repo rules

Rules for this repo only; the user's own cross-repo preferences live in their own global instructions. How to run the app and the structure are in `README.md`; the data model is `server/app/models.py`. `README.es.md` is its Spanish version, and `CHANGELOG.es.md` is the Spanish version of `CHANGELOG.md`: when one changes, change the other in the same edit. Each skill has a README next to its `SKILL.md`.

## Config

- There is no Firebase and no login any more: the app is local and meant to be shared with colleagues. There is no config file to fill in; the only per-install state is the database at `data/career-mode.db` (gitignored), which is always that file, and the backups always go to `backup/` (gitignored).
- `.env` (gitignored, template in `.env.example`) holds what the app needs and `profile/profile.md` doesn't have: the language of the app (`APP_LANGUAGE`, `en` by default or `es`), the Gemini key the `write-daily-post` skill uses, the address, password and SMTP server the applications are emailed with (`EMAIL_ADDRESS`, `EMAIL_PASSWORD`, `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, through `POST /api/mail/send` and `server/app/mailer.py`), the Google Calendar ID the Calendar's Google Calendar button reads (`GOOGLE_CALENDAR_ID`), the CV the skills attach (`CV_PDF_PATH`, a PDF that `/setup` copies to `profile/cv.pdf`), plus an optional `PORT` that Settings doesn't list. All but the port can be edited from Settings in the app; the list the page and the API know is `ENV_VARS` in `server/app/settings.py`, so a new variable is one entry there. Never put real values in the example, and a secret never travels in a list: its full value comes only from its own route (`GET /api/settings/env/<name>/value`, for the eye icon), and only for variables marked `secret`. Any key or id added to `ENV_VARS` should be marked `secret=True` to get the masked field and the eye.
- Settings is one list in alphabetical order: the `ENV_VARS` above and, last, the profile picture (`PROFILE_PICTURE_FILE`), the one file it keeps in `profile/` (`photo.*`, through `server/app/profile_photo.py`). Nothing in Settings writes to `profile/profile.md`: the profile is edited in the file, or filled with `/read-cv`. Skills read `CV_PDF_PATH` through `GET /api/settings/env`. The Google Calendar ID used to be `CALENDAR_ID`: the old name still works until the new one is saved.

## Language of the app

- Every text the page shows is in `public/locales/en.json` and `es.json` (flat keys, like the `.strings` files of iOS), and `public/js/i18n.js` reads them: `t('key')` in JS, `data-i18n` (or `-html`, `-placeholder`, `-title`, `-aria-label`) in `index.html`. English is the default and the fallback. A new text is a new key in **both** files, with the same `{placeholders}`; no text the page shows is written in a `.js` file (the English prompts to hand an AI are the exception). The language is the `APP_LANGUAGE` setting and a change reloads the page.
- What stays in English: the server's own messages (API errors, `/docs`), the skills and the docs (`README.es.md` is the only Spanish file), and the user's own files (`profile/`), whose language is theirs.

## Data

- The database is SQLite, with Alembic migrations. Change `server/app/models.py` and run `alembic revision --autogenerate` (from the `server/` folder: `../.venv/bin/alembic revision --autogenerate -m "what changed"`; read the generated file before committing). `public/js/events.js` mirrors the event types and the closing events: change them together.
- `events` and `companies` are the tables, linked with real foreign keys. A company is an agency or a client (`companyType`), in one table, so its name is unique whichever it is. A company has no stored status: it is archived when its latest event closes the process, and active again with any later one, derived by the server (`company_status` in `server/app/crud.py`). Closing events (Rejection, Red Flag, On-hold, Offer, archive) are decided by the server (`CLOSING_EVENTS` in `models.py`), so just create the event with the right type.
- An event has a `companyId` (its client, or its agency when there is no client) and, for a client that came through an agency, a `viaCompanyId`. Its label (`companyLabel`: the company's name, or "Agency → Client") is derived from them, never stored. A `passive_message` event always has a company.
- Every form that takes a company asks for one name with an Agency (default) or Client type, and a client may have its agency in Via agency. A name that exists with the other type is refused, never duplicated: the server refuses it too (409), through the one `/api/companies`.
- An application's recruiter and link belong on the event, never on the company profile.
- Skills and scripts read and write through the API (`http://localhost:8333`, docs at `/docs`; `./run-local.sh` starts the server), never by opening the SQLite file directly: the API applies the rules above.

## Checks

- `./run-tests.sh` runs pytest on the server (`tests/test_*.py`) and `node --test` on the front end (`tests/js/`, where `setup.mjs` loads the English texts first), and `.github/workflows/tests.yml` runs it on every push. A change comes with its test; say plainly what was and wasn't checked. The front end functions a test needs are `export`ed from their module.
- Tests use invented people and companies only. `tests/test_no_personal_data.py` fails when anything from the real `profile/profile.md` is in a tracked file, and is skipped where there is no such file (a fresh clone, CI).
- `./run-local.sh` starts the server (and sets up `.venv`); `./stop.sh` stops it. The server isn't restarted by editing JS, HTML or CSS (those are served as they are), but a change to `server/` needs a restart.

## Git

- Work in this checkout, on the branch already checked out: never create, switch or rename a branch (the user makes their own) and never use a worktree.
- Never commit on your own: leave the changes in the working tree so the user reads the diff first, and commit only when they run `/commit` (`.claude/skills/commit`: default author, one short line, no Claude co-author).
- Never push: the user does.

## The user's own data

- Everything personal lives in `profile/`, where git ignores everything except `README.md` and the `*.example.*` files (an invented person): `profile/profile.md` (contact details, birthdate, salary range, roles, stack, bio, work history, and the rules for presenting them) and `profile/outreach.md` (the message templates the Outreach tab shows). `./run-local.sh` makes each of them from its example on the first run, and `profile/README.md` explains how to fill `profile.md` from a public CV with an AI.
- Read `profile/profile.md` whenever a task needs personal data, and never copy any of it into a tracked file, a test, a skill or an example: tests and examples use invented people and companies, and skills say where to read a value, never what it is. The server serves only `profile/outreach.md` and `profile/profile.md` (or their examples) from there, to the Outreach tab and the My Profile page, which only show them, and the picture (`profile/photo.*`) to Settings.
- The profile mirrors the user's latest CV, which is the source of truth: titles, bullets and each role's own "Tech:" line. When the CV changes, update the profile to match. Follow its "Rules for presenting me" section, when it has any (it is optional), everywhere (profile text, messages, forms), for instance not overselling anything the user is still learning.
- Skills live in `.claude/skills/`, each with a README next to its `SKILL.md`.

## Outreach messages

- The messages (`profile/outreach.md`, started from `profile/outreach.example.md`; `profile/README.md` explains the format) have one text per language the user writes in (the example has Spanish and English): add every language together. Skills look a message up by its title, so keep the titles.
- A rejection with no reason given defaults to the note "Other candidates.", not "No reason given."

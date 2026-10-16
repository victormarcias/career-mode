---
name: setup
description: Set up career-mode for the person who just forked or cloned it: check the requirements, start the app, offer to keep their copy as a fork or as a private repo, then walk through the personal setup (CV and profile, messages, picture, Google Calendar, Gemini key) one question at a time, each with options and a way to skip. Use whenever the user says "set this up", "setup", "first time" or "get me started", or invokes /setup. Safe to run again: it skips what is already done.
---

# Set up career-mode

Everything personal ends up in files git ignores (`profile/`, `data/`, `.env`), so nothing in this skill puts personal data in a tracked file, and nothing is ever committed. Talk to the user in the language they write in. The repo's own text stays in English.

Ask with the question tool (`AskUserQuestion`): **one thing at a time**, with the answers as options, and always a "Skip for now" option. Say in one line what each step did. Never ask again about something they skipped in this run. If the user asks you to stop, stop and say how to continue later (`/setup` again).

Never read a Job Board Platform (LinkedIn, etc.) by any tool. A link to one is only written down as given.

## 1. Look around (no questions)

Run these and show a short checklist of what is fine and what is missing:

- `uname -s`: Darwin or Linux. On anything else (Windows) say the scripts need WSL, and stop.
- `python3 --version`: 3.10 or newer. If not, say so and how to install it, and stop.
- `git --version` and `curl --version`: both are needed (the skills use `curl`).
- `gh --version` and `gh auth status`: only needed to fork or to make a private copy (step 3). If it is missing, say so when that step comes.
- Whether the app already runs: `curl -s -o /dev/null -w '%{http_code}' http://localhost:8333/`.

## 2. Start the app

`./run-local.sh`. The first run creates `.venv`, installs the packages and creates `.env`, `profile/profile.md`, `profile/outreach.md` and the database, so it can take a minute. If it fails, show the last lines it printed and stop. Otherwise confirm with `curl -s http://localhost:8333/api/settings/env`.

From here on, everything is read and written through the local API (`http://localhost:8333`, docs at `/docs`), never by opening the SQLite file or editing `.env` by hand.

To know what is already done (so a second run skips it): the settings come from `GET /api/settings/env` (look at `isSet` of `CV_PDF_PATH`, `EMAIL_ADDRESS`, `EMAIL_PASSWORD`, `GOOGLE_CALENDAR_ID`, `GEMINI_API_KEY`), the picture from `GET /api/settings/photo` (null when there is none), and whether the profile and the messages are still the examples from the `X-Profile-Example` header of `curl -s -D - -o /dev/null http://localhost:8333/profile.md` and of `/outreach.md` (`true` means still the example; the routes answer GET, not HEAD).

## 3. Where the user's copy lives

Skip this step if this folder is not a git repository (they downloaded a zip): say that updates will not be pulled automatically.

Find out whether this is the original repository or already the user's copy: `git remote get-url origin`, and, if `gh` is logged in, `gh repo view --json nameWithOwner,viewerPermission,isFork,visibility`. If `viewerPermission` is `ADMIN` or `WRITE`, it is already their repository: say so and go on. Otherwise they cloned someone else's repository: ask what to do, with these options and what each one means:

1. **Fork** (public): `gh repo fork --remote`. `origin` becomes their fork and `upstream` the original, so `gh repo sync` pulls updates and they can send pull requests. A fork of a public repository is public and shows "forked from" on their GitHub profile.
2. **Private copy**: ask the name (default `career-mode`), then `git remote rename origin upstream` and `gh repo create <name> --private --source . --remote origin --push`. It is not linked to the original (`upstream` is there to pull from by hand) and nobody sees it.
3. **Keep it as it is**: nothing changes. Good for trying it out.

Either way nothing personal is uploaded, because git ignores `profile/`, `data/`, `backup/` and `.env`. Before creating or pushing anything, check that: `git check-ignore -q profile/profile.md profile/cv.pdf data/career-mode.db .env` must succeed, and `git status --short` must show nothing under `profile/` except the README and the examples. If it does not, stop and say what is not ignored. If `gh` is missing or not logged in, say `gh auth login` is needed and offer to continue with option 3.

The choice they make is their consent: do not push anything else, and never push or commit later unless they ask.

## 4. Personal setup

Each item below is one question (with "Skip for now") and, when answered, one action. Skip an item that is already done, and say so. Values the user gives you (a key, a calendar address) are secrets: send them to the API in a request body (`-d @-` with a heredoc) so they are not left in a command line, and never repeat them in what you say, only that they are set.

**a. CV.** Never fill it in from somewhere the user did not point you to: do not read it out of `profile/profile.md`, the git history, their GitHub profile or anything else on your own. If `CV_PDF_PATH` is already set in the settings, say so and offer to keep it or to replace it; use it only if they choose to. "Where is your CV?" Options: a PDF file on this computer (ask the path); skip.

For a file: check that it exists, that it is a PDF (its first bytes are `%PDF-`) and that it is **at most 1 MB**; if it is bigger, say so and ask for a smaller one (the app refuses it). Copy it to `profile/cv.pdf` with `cp` (if one is already there, ask before replacing it; git ignores it) and set the setting to that copy: `curl -s -X PUT -H 'Content-Type: application/json' -d '{"values":{"CV_PDF_PATH":"profile/cv.pdf"}}' http://localhost:8333/api/settings/env` (a 422 says what is wrong). This file is what the applying skills attach and upload, and it is a copy: when the CV changes, run `/setup` again.

**b. Profile.** If the profile is still the example and there is a CV (the file): offer to fill it now, with the options "Yes, from my CV" and "Skip for now". If yes, follow `/read-cv` (with that path): it shows what it will change and asks, in one numbered message, for what the CV cannot tell. Tell the user before it starts that this is the long part, that every item can be skipped for now (or the whole list with `skip`) and that a skipped item is left as `(not set)` and asked for later, when a form needs it. Do not repeat its questions yourself. If they skip the profile entirely, say that the profile stays as the example's, that the My Profile page says so, and that `/read-cv` (or `/setup` again) fills it later.

**c. Messages.** "Do you have your messages (the texts you send to recruiters) in a document?" Options: yes, a link to a public document; no, write them for me from my profile; skip. Follow `profile/README.md` ("Make your messages yours"): same six titles and structure as `profile/outreach.example.md`, one text per language the user writes in, copied word for word from the document (Google's own markdown export loses the code blocks, so rebuild them), or drafted from `profile/profile.md` in their tone. Show the result and wait for their OK before writing `profile/outreach.md`; keep a copy of the previous file in `profile/backups/` (as `/read-cv` does: folder mode 700, file mode 600).

**d. Picture.** "Do you have a profile picture to use in forms?" Options: yes, a file on this computer (ask the path); I will upload it in Settings; skip. For a file: a PNG or JPEG of at most 1 MB (check the size and the type first), then `curl -s -X PUT -H 'Content-Type: application/octet-stream' --data-binary @"<path>" http://localhost:8333/api/settings/photo`. A 422 says what is wrong.

**e. Email** (to send the applications). "Do you want the applications to be sent by email from your own address?" If yes, ask for the address (`EMAIL_ADDRESS`, not a secret) and the password (`EMAIL_PASSWORD`, a secret). For a Gmail address it has to be an app password, not the account one: Google account, Security, turn on 2-Step Verification, then App passwords, make one called `career-mode` and paste it (Google shows it as four groups of letters; spaces are fine). Any other provider works too if it has an SMTP server: ask for its server (`EMAIL_SMTP_HOST`) and port (`EMAIL_SMTP_PORT`, 465 or 587) and what password it wants; for Gmail leave both alone, they default to Gmail's. Say that the skills then send through the app with no browser; without it `/apply-email` stops and says to set it up. Once it is saved, offer a test (options: "Send me a test email", "Skip"): if yes, `POST /api/mail/send` to **their own address only**, with `attachCv: false`, the subject `career-mode test` and a one-line body, and say what came back (a 502 says what to check, usually the app password). Never send a test to anyone else.

**f. Google Calendar** (optional). "Do you want the Calendar's Google Calendar button to import your interviews?" If yes, explain what to give: the calendar's ID (Google Calendar, Settings, the calendar, Integrate calendar), which only works if the calendar is public with "See all event details", or its secret address in iCal format, which also works for a private one. Set `GOOGLE_CALENDAR_ID` the same way as the CV link, as a secret.

**g. Gemini key** (optional). "Do you want the daily post to come with an image?" If yes, ask for the API key and set `GEMINI_API_KEY` as a secret.

**h. The browser** (only for web forms). `/apply-site` fills the application forms of other sites by driving the user's Chrome through the Claude in Chrome extension; emails do not need it. Tell them so, and ask whether they have it; if not, say where it is set up and that everything else works without it.

## 5. Finish

- Open the app: `open http://localhost:8333` on macOS, `xdg-open` on Linux.
- Say, in a short list, what was set and what was skipped, and where each skipped thing is done later: Settings (CV file, email address and password, Google Calendar ID, Gemini key, picture, database and backup folders), `profile/profile.md` or `/read-cv` (the profile), `profile/outreach.md` (the messages), or running `/setup` again.
- Remind them the app is started with `./run-local.sh` and stopped with `./stop.sh`, and that the Calendar's **+ Application** and the sidebar's **Pending** page are where applications start.

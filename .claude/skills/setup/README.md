# setup

Gets a fresh fork or clone of career-mode working, step by step, asking for each thing with options and a way to skip.

- **Checks:** macOS or Linux (WSL on Windows), Python 3.10+, `git`, `curl` and, for the next step, `gh`.
- **Starts the app** with `./run-local.sh` and talks to it through its API from then on.
- **Where your copy lives:** if you cloned someone else's repository, it offers a public **fork** (linked to the original, to pull updates), a **private copy**, or leaving it as it is. Before it creates or pushes anything it checks that `profile/`, `data/` and `.env` are ignored by git, and it never commits or pushes later unless you ask.
- **Your own setup**, one question at a time, each skippable: the CV (a PDF of at most 1 MB, copied to `profile/cv.pdf`), the profile (through `/read-cv`: its long list of questions can be skipped for now, and what is skipped is left `(not set)` and asked for later), your messages (from a document, or drafted from your profile), your profile picture, your email address and password (so the applications are sent by email from the app), the Google Calendar ID and the Gemini key (both optional), and a word on the Chrome extension that only the web forms need.
- **Safe by construction:** keys and calendar addresses go to the API in a request body and are never repeated back; it never reads a Job Board Platform; nothing personal goes in a tracked file.
- **Use it:** `/setup`, the first time and whenever you want to finish what you skipped. It is safe to run again: it skips what is already done.

Instructions: [SKILL.md](SKILL.md).

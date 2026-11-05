# setup

Gets a fresh fork or clone of career-mode working, step by step, asking for each
thing with options and a way to skip. It checks the requirements (macOS or
Linux, Python 3.10+, `git`, `curl`, `gh`), starts the app with `./run-local.sh`,
offers to keep the copy as a public fork or a private repo after checking that
`profile/`, `data/` and `.env` are ignored, and then asks one question at a time
for the CV, the profile (through `/read-cv`), the messages, the picture, the
email account, the Google Calendar ID and the Gemini key.

Keys and addresses go to the API in a request body and are never repeated back,
nothing personal goes in a tracked file, and it never commits or pushes unless
asked. It is safe to run again: it skips what is already done. Run it as
`/setup` the first time and whenever the skipped parts should be finished.
Instructions: [SKILL.md](SKILL.md).

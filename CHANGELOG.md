# Changelog

All notable changes to career-mode are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

[Español](CHANGELOG.es.md)

## [Unreleased]

### Added

- **Archive (ghosted) in an event's form:** a button left of Delete, in the form that edits an event, archives that event's company by hand (👻 Ghosted), as the company card's Archive does. It shows while the company is active, and not on a queued link or an archive.
- **`./backup-data.sh --open`:** opens the backup folder at the end also when the script is not run from a terminal (from a pipe or a tool); from a terminal it already did.
- **`/follow-up-email-application`:** follows up, without asking, the applications sent by email that got no answer in 7 days or more, once each, as a reply on their own Gmail thread with the Application Follow-up Message in the language of the application, and logs each one in the Calendar as a "Follow up" note.
- **Collapsible menu:** the sidebar can show only its icons, with the favicon in place of the logo and a tooltip on each icon. A toggle at the top right of the logo does it, and it does it by itself when the window is too narrow for the content (under 1,240 px); a choice made with the toggle holds until the window crosses that width.
- **How an archived company was closed:** the tag of an archived company in Companies says the reason (👻 Ghosted, ❌ Rejected, 🚩 Red flag, ⏸️ On hold or 🎉 Offer), in a color like the emoji's, and the API says it with a derived `closedBy` on every company. Ghosted is an archive by hand.
- **Sync Google Tasks:** a button next to Google Calendar's in the Calendar reads the open tasks of the user's Google Tasks (through the Google Tasks API), queues every job link in them as a pending application, once, and marks those tasks as done. Without its three settings (new, with the steps) it says so and links to Settings; the Google Calendar button does the same.
- **`/sync-aiapply`:** reads the AIApply.io notifications in Gmail and logs each positive reply from a company (an interview invitation, an assessment, a follow-up) as a web application, once, with the company as an agency or a client. Its "Not this time" notices are moved to the trash once there is nothing left to log from them.
- **`/reply-rejected`:** finds the rejections companies sent to the user's Gmail and replies to each one, once, thanking them and saying they will stay in touch, archives the email, and logs the rejection in the Calendar.
- **`/check-email`:** sorts the recent Gmail and runs `/sync-aiapply`, `/reply-rejected` and `/reply-recruiter` on what it finds.
- **`/wake-up`:** the start-of-day routine in one command: runs `/check-email` and then `/apply-pending`.

### Changed

- **`/apply-pending`:** applies to hybrid and on-site roles too, removes without asking a link whose process has an AI interview at any stage, and notes a general careers page (a list of openings, a talent signup) in the profile for `/submit-profile` instead of leaving it pending.
- **Links in emails stay as they are:** the Gmail connector rewrites every link it sends into a `google.com/url` redirect, so a reply with a link (from `/check-email` when the user asks to answer a thread, or a `/follow-up-email-application` message with a link) goes through the app's `POST /api/mail/send`, which now takes `inReplyTo` (the `Message-Id` of the email it answers) to send it on that thread.
- **Companies tabs follow the company:** typing a name in the search picks the Active or Archived tab it is found in, and a link to a company (the building in the Calendar form, a "via" link) opens the tab it is in.
- **Company arrow in the Calendar form:** it is a building icon that goes to the company's card in Companies, instead of an arrow that opened its website or LinkedIn page in another tab; the card shows them.
- **Company in every new event:** the Update form, the New application form and the Google Calendar sync ask for one Company, with an Agency (default) or Client tag next to it. A client has an optional Via agency. Typing the name of a company that exists picks it, and its tag follows. A name that already exists with the other tag is refused, so a company is not created twice.
- **Passive messages:** a passive message needs an agency or a client, so a recruiter of a company that hires directly is logged against the client. Existing databases are migrated on start.
- **`/reply-recruiter`:** logs a direct employer as a client, and an agency as an agency.
- **`/apply-pending`:** a JD Post is discarded when it was last updated a month ago or more, and no technology rules a post out any more: Python or JavaScript is what counts, and the other tools can be learned.
- **Company Home:** the New application form no longer requires it for an agency: it is optional for every company, and a link that is given still has to be a company page on LinkedIn.
- **Skills' output:** `/sync-aiapply`, `/reply-rejected`, `/check-email`, `/reply-recruiter` and `/apply-pending` no longer report what they did, unless the command has `--verbose`. Failures, what needs the user and the reply drafts are always shown.
- **One company, one API:** agencies and clients are one list of companies, each an agency or a client (`companyType`), with its name unique whichever it is: the same name can no longer be made twice, by the API or by a form. An event has a `companyId` (its client, or its agency when there is no client) and a `viaCompanyId` (the agency a client came through). A company's status is derived from its events instead of stored. The Companies page, Follow Up, the forms, the Google Calendar sync, the backups (`companies.csv` has a `company_type` column, and the older backup files still load) and the skills use it. Existing databases are migrated on start.

### Removed

- `/api/agencies` and `/api/clients`: use `/api/companies`, with `?companyType=agency` or `client` to keep one kind, and `?companyId=` on `/api/events` in place of `?agencyId=` and `?clientId=`.

## [0.1.1] - 2026-10-20

### Added

- **Pending:** several links can be queued at once, one per line. Each link is checked and queued in order, and a summary says what was queued, skipped or failed. What could not be queued stays in the box.
- **Backups:**
  - `profile.pdf` and `outreach.pdf` in `backup/profile/`, printed with Chrome or Chromium.
  - A copy of the `.env` in `backup/env/env`, readable only by the user.
  - The daily posts, with their log.
  - The backup folder opens after a run from a terminal.
  - `restore-backup.sh` restores the `.env` and the daily posts, and keeps a safety copy of both before replacing them.
- **CLI:** `profile-pdf` and `outreach-pdf` commands in `server/cli.py`.
- **Skills:**
  - `/commit`: commits on the current branch with the default author and a one-line message, and never pushes.
  - `/write-daily-post` saves each post in `profile/daily-posts/` with a topic line and a `log.csv` that picks the next topic.
- **Tests and CI:** a pytest suite for the server, a Node suite for the front end, `run-tests.sh` and a GitHub Actions workflow that runs both on every push. A test fails when anything from the real profile is in a tracked file.
- **Project:** `.github/FUNDING.yml`, and a Git section in `CLAUDE.md`.

### Changed

- **Follow Up:** the days count from the last application instead of the first event. A recruiter's message counts as an application, and a company with none falls back to its last event.
- **Spanish:** the interface and `README.es.md` use neutral Spanish.
- **`/apply-pending`:**
  - Looks the link up first, so the same JD Post is not applied to twice.
  - Chooses the channel from what the JD Post says, writes the email subject and picks the message in the JD Post's language.
  - Works through the pending queue when run without a link.
  - Reads LinkedIn JD Posts, with WebFetch first and then in Claude in Chrome, and opens Chrome for any other page it cannot read.
- **`/apply-email` and `/apply-site`:** both report whether the application was sent or why it stopped. `/apply-site` stops at captchas and accounts to create, leaves the form open when stuck, and answers form questions on its own.
- **`/reply-recruiter`:** one Calendar entry per conversation, only the technologies the recruiter asks about, and no need to read another skill.
- **`/write-daily-post`:** the image prompt asks for correct spelling and minimal text, the post text is shown next to the image, and a bad image is discarded and its topic reused.
- **`/setup`:** offers the backup's `outreach.md` and can send a test email to the user's own address.

### Removed

- The `BACKUP_DIR` and `CAREER_MODE_DB` settings. The database is always `data/career-mode.db` and the backups always go to `backup/`. Old lines in a `.env` are ignored.

### Fixed

- `/apply-pending` logged an application before it was sent. It now logs it only once it went out.
- `/read-cv` creates its backups folder with private permissions.
- A restored `.env` can no longer move the database or end up in a folder that git does not ignore.

### Security

- The `.env` copy in the backup is readable only by the user, and always lives in `backup/`, which git ignores.

## [0.1] - 2026-10-13

Initial release.

[Unreleased]: https://github.com/victormarcias/career-mode/compare/0.1.1...HEAD
[0.1.1]: https://github.com/victormarcias/career-mode/compare/0.1...0.1.1
[0.1]: https://github.com/victormarcias/career-mode/releases/tag/0.1

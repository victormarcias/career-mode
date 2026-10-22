# Changelog

All notable changes to career-mode are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

[Español](CHANGELOG.es.md)

## [Unreleased]

### Added

- **`/sync-aiapply`:** reads the AIApply.io notifications in Gmail and logs each positive reply from a company (an interview invitation, an assessment, a follow-up) as a web application, once, with the company as an agency or a client.
- **`/reply-rejected`:** finds the rejections companies sent to the user's Gmail and replies to each one, once, thanking them and saying they will stay in touch, archives the email, and logs the rejection in the Calendar.
- **`/check-email`:** sorts the recent Gmail and runs `/sync-aiapply`, `/reply-rejected` and `/reply-recruiter` on what it finds.

### Changed

- **Company in every new event:** the Update form, the New application form and the Google Calendar sync ask for one Company, with an Agency (default) or Client tag next to it. A client has an optional Via agency. Typing the name of a company that exists picks it, and its tag follows. A name that already exists with the other tag is refused, so a company is not created twice.
- **Passive messages:** a passive message needs an agency or a client, so a recruiter of a company that hires directly is logged against the client. Existing databases are migrated on start.
- **`/reply-recruiter`:** logs a direct employer as a client, and an agency as an agency.

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

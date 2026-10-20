---
name: apply-email
description: Send a job application by email from the user's own email address through the app's own API (no browser), with the CV attached. Use this whenever the user asks to email a recruiter or send an application by mail, including as the delivery step for /apply-pending when a JD Post's `applyType` is `email_apply` (the JD Post gives an email address to apply to).
---

# Apply by email

The sender is the address of the `EMAIL_ADDRESS` and `EMAIL_PASSWORD` settings (Settings, or `/setup`; Gmail by default, any provider with an SMTP server through `EMAIL_SMTP_HOST` and `EMAIL_SMTP_PORT`), and the app sends through it itself: no browser, no Claude in Chrome. The contact email, the user's name and the expected salary range come from `profile/profile.md`, and the CV from the `CV_PDF_PATH` setting (a file); read them at run time. A value that says `(not set)` is asked of the user, never guessed.

Check first that email is set up (if the request can't connect, `./run-local.sh` starts the app): `curl -s http://localhost:8333/api/settings/env` and look at `isSet` of `EMAIL_ADDRESS`, `EMAIL_PASSWORD` and `CV_PDF_PATH`. If one is not set, say which and stop: the user sets it in Settings (for Gmail the password is an app password, made in the Google account, Security, 2-Step Verification, App passwords), or by running `/setup` again. Never ask for the password in chat and never repeat it.

**The sign-off** is the message's own: the user's full name (the profile's), then their website, one per line, after the closing words. If the message the caller filled in ends without the name, add it above the website. Send `fromName` as that same full name, so the sender shows as a person and not as a bare address.

**Send it** with one request, to one recipient, with no CC or BCC. The body is the message of the caller, with its line breaks as they are except that a paragraph break is **one** blank line: collapse any run of blank lines to one (also after adding the salary line and the name), and leave none at the start or the end; use `--data-binary @-` with a heredoc so nothing sensitive ends up in a command line:

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  http://localhost:8333/api/mail/send -d @- <<'JSON'
{"to": "...", "subject": "...", "body": "...", "fromName": "..."}
JSON
```

The CV is attached by default (`attachCv: false` leaves it out). The answer is `{"sent": true, "from": ..., "to": ..., "attached": "cv.pdf"}`; an error comes as `{"detail": "..."}` (409 when email or the CV is not set up, 502 when the mail server refuses, with what to check). Send without asking: applying is what the user asked for, and the confirmation is not repeated per email. Stop and ask instead only for a real reason: the recipient is unclear, the JD Post asks for something the message doesn't answer (a different salary or currency, a cover letter, a video), or something fails twice. Then show the sent text in chat, with its links as clickable markdown.

**Expected salary:** every application email states the user's expected range from the profile (Work preferences → expected salary range) as one short line of the body, just before the sign-off (e.g. "My expected salary is X–Y USD per month."). Add it if the template the caller filled in doesn't already have it, and never write a different figure — if the JD Post asks for a different currency or a specific number, stop and ask the user.

This is the delivery step only — the recipient, subject, and body come from whatever's calling this (usually `/apply-pending`, which resolves the recruiter's email, the subject and the right message template first). If the user asks for this directly with an already-known recipient and message, just run the send flow above with what's given; with no subject, use the role and the user's full name, such as "Application for <role> – <full name>".

**Report back** to the caller either that it was sent (to whom) or that it was not and why: `/apply-pending` logs the application in the Calendar only when it went out, so a failed send must be said plainly and never reported as done.

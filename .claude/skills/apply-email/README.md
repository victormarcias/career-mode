# apply-email

Sends a job application by email from the user's own email address. It's the delivery step for applications whose `applyType` is `email_apply` (the JD Post gives an email address).

- **How:** one request to the app's own `POST /api/mail/send`, which sends through the SMTP server of the `EMAIL_*` settings (Gmail's by default, so Gmail needs an app password; any provider with an SMTP server works), and attaches the CV (the file of the `CV_PDF_PATH` setting). No browser and no Claude in Chrome. It sends without asking and shows what it sent; it stops only for a real reason (unclear recipient, something the message doesn't answer, a repeated failure).
- **Format:** the message goes out as it is, with one blank line between paragraphs: runs of blank lines are collapsed to one.
- **Salary and sign-off:** every email states the expected range from the profile as one line before the sign-off, which is the user's full name and then their website. The sender is shown with that name.
- **Reports back:** that it was sent, or that it wasn't and why, so the caller logs the application only when it went out.
- **Not set up:** if the email settings or the CV are missing it says which and stops: they are set in Settings, or by running `/setup`.
- **Touches:** the email account in Settings (Gmail keeps a copy of each email in its Sent folder; other providers may not). Nothing in the database.
- **Called by:** [apply-pending](../apply-pending/README.md), which resolves the recipient and message first. It also works directly with a known recipient and message.

Instructions: [SKILL.md](SKILL.md).

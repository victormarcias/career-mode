# apply-email

Sends a job application by email from the user's own address, with the CV
attached. It is the delivery step for applications whose `applyType` is
`email_apply`, called by [apply-pending](../apply-pending/README.md) with the
recipient, subject and message already chosen, and it also works directly with a
known recipient and message.

One request to the app's `POST /api/mail/send` sends it through the SMTP server
of the `EMAIL_*` settings (Gmail needs an app password), with the expected
salary range from the profile before the sign-off. It sends without asking and
reports that it went out, or why it did not, so the application is logged only
when it was sent. It stops, saying which, when the email settings or the CV are
missing. It touches only the email account in Settings, nothing in the database.
Instructions: [SKILL.md](SKILL.md).

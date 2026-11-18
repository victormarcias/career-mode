# reply

Drafts the reply to a recruiter who wrote first, on a platform or by email,
from the Proposal Reply Message in `profile/outreach.md`. `/reply --short`
gives the message as it is; plain `/reply` adapts it to answer what the
recruiter asked (English level, CV, the technologies they name, backed by
`profile/profile.md`). The salary and the email are read from the profile.

It logs the company and one `passive_message` event per conversation in the
Calendar through the local API, so nothing has to be entered by hand. The user
sends the reply; the platform is never opened. Not for JD Posts the user
applies to, which are [apply-pending](../apply-pending/README.md)'s.
Instructions: [SKILL.md](SKILL.md).

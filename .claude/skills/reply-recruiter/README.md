# reply-recruiter

Handles a recruiter who contacted the user first, on a Job Board Platform or by
email. The user pastes the message and the recruiter's profile link; the skill
analyzes it (recruiter, company, role, terms, red flags) and drafts the reply in
the message's language from the Proposal Reply Message, with the salary range
and contact email read from `profile/profile.md` and only the technologies the
recruiter names, saying honestly what the profile backs.

It records the company and one `passive_message` event per conversation in the
Calendar, adding to it when the same recruiter writes again within a week. The
user sends the reply themselves; the platform is never read, its links are only
written down as given. It touches the career-mode database through its local
API. Not for JD Posts the user applies to, which are
[apply-pending](../apply-pending/README.md)'s. Instructions:
[SKILL.md](SKILL.md).

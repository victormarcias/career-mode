# reply-recruiter

Handles a recruiter who contacted the user first, on a Job Board Platform or by email (a passive contact). The user pastes the message and the recruiter's profile link.

- **Analyzes** the message: recruiter, company (agency or direct employer), role, terms, red flags.
- **Drafts the reply** in the message's language from the "📝 Proposal Reply Message": interested, expected salary range and contact email, all read from `profile/profile.md` (see [submit-profile](../submit-profile/README.md)). The user sends it themselves on the platform.
- **Records** the agency with the recruiter, and a `passive_message` event in the Calendar (that event type always needs an agency).
- **Touches:** the career-mode database (agencies and events) through its local API. The Job Board Platform is never read, by any tool: its links are only written down as given.
- **Not for** JD Posts the user applies to: that's [apply-pending](../apply-pending/README.md).

Instructions: [SKILL.md](SKILL.md).

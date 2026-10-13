# apply-pending

Applies to a job link end to end, or clears the whole queue of `pending` applications ("Apply Bulk links"). The links come from the app's "Pending" page, which only queues them.

- **For each link:** reads the JD Post from its public page without the user's session (or takes what the user pastes): recruiter, how to apply, language, date; refuses JD Posts older than 3 weeks, skips the ones that clearly don't fit the profile, and chooses email or form from what the JD Post says, picks and fills the message template, creates the agency or client profile when it's new, logs the application in the Calendar, then hands off to [apply-email](../apply-email/README.md) or [apply-site](../apply-site/README.md) depending on `applyType`.
- **Queue run:** processes every `pending` event oldest first, replaces each completed one with the real `application` event, and leaves the ones it couldn't finish (captcha, dead link, old post) in place with a summary.
- **Touches:** the career-mode database (events, agencies, clients) through its local API, and, for web forms, the connected Chrome session (emails go out through the app's email setting). A Job Board Platform is never opened with the browser or the user's session: only a JD Post's public page is read, with WebFetch and no session; profiles and company pages are only written down as given.

Instructions: [SKILL.md](SKILL.md).

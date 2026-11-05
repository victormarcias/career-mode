# reply-rejected

Answers the companies that rejected the user and logs the rejection, from the
user's Gmail. It finds the clear rejections of the last 14 days, replies to each
once with a short thanks that says they will stay in touch, in the language of
the rejection and signed with the user's first name, and archives the thread; an
unclear one is listed for the user instead.

It logs a `rejection` event in the Calendar only for a company that already has
a process there, never starting one, with the note "Other candidates." when no
reason is given. It skips the reply, but still logs, for a thread already
answered, a `no-reply` sender and AIApply's notices. It replies only to the
sender, adds no link or question, and is silent unless the command has
`--verbose`. It touches Gmail and the career-mode database. Called by
[check-email](../check-email/README.md), and it also works on its own.
Instructions: [SKILL.md](SKILL.md).

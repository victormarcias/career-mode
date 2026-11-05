# sync-aiapply

Brings the positive replies that AIApply.io got from companies into the
Calendar, and clears its "Not this time" notices, from the user's Gmail. It
reads the last 7 days of AIApply's notifications and, for each new interview
invitation, assessment or follow-up, logs one `application` event (type
`web_form`, `Recruiter: AIApply.io` and the position in the notes) with its own
AIApply link, so the duplicate check is exact. It finds or creates the company
as `/apply-pending` does and never changes an existing event.

A "Not this time" email goes to the trash once there is nothing left to log from
it, and one whose rejection is still to be logged waits for
[reply-rejected](../reply-rejected/README.md). It never sends, replies, labels
or archives anything, and is silent unless the command has `--verbose`. It
touches the career-mode database and Gmail, read only except for that trash.
Instructions: [SKILL.md](SKILL.md).

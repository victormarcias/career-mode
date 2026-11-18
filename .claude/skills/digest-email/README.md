# digest-email

One command for the mailbox. It reads the last 2 days of the user's Gmail, sorts
each thread and handles it: rejections get the Application Rejected Message of
`profile/outreach.md` and are logged in the Calendar, and recruiters who wrote
first go to [reply](../reply/README.md). The threads that propose or
confirm an interview get the `Interviews` tag, the rejections get `Rejected`,
the ones that ask the user to do something get `Needs Attention`, and the email
applications whose thread went quiet for 7 days get one follow-up on that same
thread, tagged `Follow Up`. The tags are the ones already made in Gmail.

Once a thread's Calendar entry exists it is archived, and so is an automatic
"thanks for applying" confirmation; a thread that needs the user, or an
interview, never is. It ends with a table of Name, Subject and Action for what
it did. It never opens a link of an email. It touches Gmail (read, tags and
archive), the career-mode database through its local API and the skills it
calls. Instructions: [SKILL.md](SKILL.md).

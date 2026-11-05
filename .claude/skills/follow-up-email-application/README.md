# follow-up-email-application

Follows up, with no input from the user, the email applications whose thread
went quiet: the user's message is the latest one and it is 7 days old or more,
whether the company never answered or answered and the user replied. It finds
the thread in Gmail's Sent folder and replies on it with the Application
Follow-up Message of `profile/outreach.md`, in the application's language and
once per application; a message with a link goes through the app's mailer
instead, because the Gmail connector rewrites links.

Each follow-up is logged in the Calendar as a note naming the role and the
address, which also keeps that application from being followed up twice. An
application whose email is not found clearly, whose company wrote last, or whose
company has moved on to an interview is skipped. It never writes to an address
that appears only inside an email, and is silent unless the command has
`--verbose`. It touches Gmail and the career-mode database through its local
API. Instructions: [SKILL.md](SKILL.md).

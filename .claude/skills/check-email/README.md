# check-email

One command for the mailbox. It reads the last 2 days of the user's Gmail, sorts
each thread and runs the skill that handles it: AIApply's positive notifications
go to [sync-aiapply](../sync-aiapply/README.md), rejections to
[reply-rejected](../reply-rejected/README.md) and recruiters who wrote first to
[reply-recruiter](../reply-recruiter/README.md). A company asking for something
(an interview time, an assessment, a form) is only listed for the user, and so
is any unclear thread.

Once a thread's Calendar entry exists it is archived, and so is an automatic
"thanks for applying" confirmation, which only confirms and asks for nothing; a
thread that needs the user, or whose skill stopped, never is. It never sends or
replies by itself, never opens a link of an email, and is silent unless the
command has `--verbose`. It touches Gmail (read and archive) and the skills it
calls. Instructions: [SKILL.md](SKILL.md).

---
name: wake-up
description: The morning routine in one command: bring the chat group's links into Pending (/links-inbox), apply to everything pending (/apply-pending) and digest the email (/digest-email). Use whenever the user invokes /wake-up or asks to start the day.
---

# Wake up

One command, three steps, in this order, each through the Skill tool and with
the days or `--verbose` the user gave passed on:

1. `/links-inbox`, to queue the new links of the user's chat group. If it stops
   (no credentials, not signed in, the bot is busy), say so in one line and go
   on.
2. `/apply-pending`, to work through the whole queue.
3. `/digest-email`, for the mailbox.

End with what those skills end with (the applications table and the email
table), and nothing else. Nothing is committed.

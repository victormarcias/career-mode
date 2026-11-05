# wake-up

The start-of-day routine in one command: it runs
[check-email](../check-email/README.md), then
[follow-up-email-application](../follow-up-email-application/README.md) and then
[apply-pending](../apply-pending/README.md), one after the other. A step that
stops is reported and the next one still runs, and the app is started once first
if it is not running.

Each step shows what it always shows (what needs the user, the reply drafts, the
applications table, failures), and `--verbose` is passed on to every step.
Adding a step is one more line in the list of [SKILL.md](SKILL.md). It touches
nothing by itself; the skills it runs do the rest.

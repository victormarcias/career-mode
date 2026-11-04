# wake-up

The start-of-day routine in one command. It runs, in this order:

1. [check-email](../check-email/README.md): sorts the recent Gmail and runs the skills that handle it.
2. [apply-pending](../apply-pending/README.md): works through the queue of pending applications.

- **A step that stops** is reported and the next one still runs; if the app is not running, it is started once first.
- **Output:** what each step always shows (what needs the user, the reply drafts, the applications table, failures); `--verbose` is passed on to every step and adds one line per step at the end.
- **Adding a step** is one more line in the list of [SKILL.md](SKILL.md).
- **Touches:** nothing by itself; the skills it runs do the rest.

Instructions: [SKILL.md](SKILL.md).

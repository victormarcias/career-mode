---
name: wake-up
description: The user's start-of-day routine in one command: runs /check-email, /follow-up-email-application and /apply-pending, one after the other. Use whenever the user invokes /wake-up or asks to start the day, run the morning routine or do the daily round.
---

# Start the day

One command for the start of the day. It does nothing by itself: it runs the skills below with the Skill tool, in this order, without asking before each one (the command is the order).

## The steps

1. `/check-email`: sorts the recent Gmail and runs the skills that handle it. Pass on the days the user gave, if any.
2. `/follow-up-email-application`: follows up the email applications that got no answer, once each. It runs after `/check-email` so that an answer or a rejection that just came in is logged first, and the application is skipped.
3. `/apply-pending`, with no link: works through the queue of pending applications.

Pass `--verbose` to each step when the command has it. A new step is one more line in this list, in the place it should run.

## When a step stops

A step that stops (the app is not running, Gmail can't be read, something only the user can do) is reported and the next one still runs. When the app's API (`http://localhost:8333`) doesn't answer, start it with `./run-local.sh` once, before the first step, instead of letting each step find out.

## Finish

Each step shows what it always shows (what needs the user, the reply drafts, the table of `/apply-pending`, failures). Add nothing of your own unless the command has `--verbose`; with it, end with one line per step saying what it did. Nothing is committed.

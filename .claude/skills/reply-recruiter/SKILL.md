---
name: reply-recruiter
description: Handle a recruiter who contacted the user first, on a Job Board Platform or by email (a "passive contact"). The user pastes the recruiter's message and usually their profile link; this analyzes it, drafts the reply in the message's language (interested, expected salary range, contact email), and logs the agency plus the recruiter in career-mode's database as a passive message. Use whenever the user pastes a message from a recruiter, from a platform or an email, and says something like "a recruiter wrote to me", "a recruiter sent me a proposal", "passive contact" or "reply that I'm interested", or invokes /reply-recruiter.
---

# Reply to a recruiter's message

For a recruiter who reached out first (a **passive contact**), not for a JD Post the user is applying to — those go through `/apply-pending`. The user pastes the message (and, ideally, the recruiter's profile link). You analyze it, draft the reply, and record who made contact. The user sends the reply themselves on the platform.

## Hard rule: never read the platform

Nothing on a Job Board Platform (LinkedIn, etc.) is opened, with no tool: a platform can flag automated activity and restrict the account. The recruiter's message comes pasted by the user, and the recruiter's profile link, the company's page and any link to a JD Post are only **written down as given**. Work from what the message itself gives (name, title and company in the signature) plus the company's own website or a web search; if something is missing, leave it out or ask the user, never fill it in from the platform. And never send anything on the platform: the reply is only shown in chat.

## 1. Analyze the message

Give the user a short analysis first, in their chat language (`profile/profile.md`, Chat language), covering:

- **Who:** the recruiter (name, and title if the message gives it; the profile link only as the user gave it) and the company, and whether it's an **agency/consultancy** (it places people with clients) or the **direct employer**. Research a new company with WebFetch/WebSearch on its own website (what it actually does), never on the platform — don't guess.
- **The role:** title, key requirements or mindset they describe, seniority, English level asked for.
- **Terms:** modality (contractor vs. employee), currency, remote/hours/timezone, and any compensation they mention.
- **Red flags and fit:** not remote, local currency or pay well under the expected range, unpaid test, vague role. Say plainly whether it looks worth pursuing. If the user wants to decline instead, write a short, polite decline and log it the same way.

## 2. Draft the reply

- Use the **📝 Proposal Reply Message** in this app's Outreach → Messages tab (it shows `profile/outreach.md`), in the **language of the recruiter's message** (Spanish or English). Fill in the recruiter's first name and the role. If the text is still the example's placeholder (the Messages tab shows a banner while that is so), don't use it: ask the user to write it first (`profile/README.md` explains how).
- It says the user is interested, states the **expected salary range** and gives the **contact email**. Take both from `profile/profile.md` at run time (Basics → Email, Work preferences → expected salary range) — never retype them from memory, so a change there flows through.
- **Technologies: mention only the ones the recruiter asks about or names for the role,** and none of the rest of the profile's stack, even if it would look good. For each one, say what the profile backs (where, when, for how long) and, if it is old or partial, say so plainly. When the recruiter asks about a technology the profile doesn't cover, ask the user instead of improvising.
- Adapt the modality clause to what the recruiter offered (contractor in USD is the default). If the message asks something the template doesn't answer and the profile doesn't cover it, ask the user instead of improvising.
- Show the reply in chat as a copyable block, and links as clickable markdown outside it. The user sends it where the message came from, the platform or the email.

## 3. Record the agency and the recruiter

Through the local API at `http://localhost:8333` (docs at `/docs`; if a request can't connect, `./run-local.sh` starts the server), with `curl -s -H 'Content-Type: application/json'`: `GET`, `POST` and `PATCH /api/agencies` (and `/api/agencies/<id>` to change one), and `GET` (filter with `?agencyId=<id>`), `POST` and `PATCH /api/events` (`/api/events/<id>`). Errors come back as `{"detail": "..."}`. A passive message is always logged against an **agency**: the company the recruiter works for, even when it turns out to be the end employer. The event type requires one, and the API answers 422 without an `agencyId`.

1. **New company?** `GET /api/agencies` and look for it **by name (ignoring case)**. If it exists, reuse its `id` and leave its profile alone, only adding the recruiter's profile URL to its `recruiters` if it's missing (`PATCH /api/agencies/<id>` with the full list: it replaces the list). If it doesn't, research it and `POST /api/agencies` a real profile: `name`, `type` (what it does, in one line), `website`, `linkedin`, `recruiters` (the recruiter's profile URL). The server makes the `id` and refuses a second agency with the same name.
2. **Log it in the Calendar, once per conversation.** The user runs this command for each message of a thread, and a thread is one entry, not one per message. First `GET /api/events?agencyId=<id>` (quote the URL) and look for a `passive_message` from the same recruiter (the name is in its notes) dated today or within the last 7 days. If there is one, it is the same conversation: don't create another. `PATCH /api/events/<id>` with its `notes` as they are plus a new paragraph for this message (what they asked and what the reply says), keep its date, and if the message is the same one already logged, say so and change nothing. Only when there is none, `POST /api/events` with `event: 'passive_message'`, today's `date`, the `agencyId`, no `jdUrl`, and `notes` covering: that it was a passive contact (on a platform or by email), the recruiter (name, title, profile link), the role and what they asked for, the terms, and what the user replied (interested, salary range, email). Never skip this step. There's no company label to fill in: the calendar derives it from the agency.

Don't touch anything else, and say what you wrote.

## 4. Finish

Reply in chat with: the analysis, the draft reply, and what was saved (agency created or reused, recruiter added, the Calendar event created or, for a thread already logged, updated). Nothing is sent and nothing is committed.

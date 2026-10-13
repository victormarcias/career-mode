---
name: apply-pending
description: Apply to a job the user sends — a JD Post link from a Job Board Platform (LinkedIn, Indeed...), a recruiter message, or any other portal link — or process the whole queue when the user says "Apply Bulk links" (or similar, e.g. "process the pending ones"). Use this whenever the user pastes a JD Post link and asks to apply, forwards something from a recruiter, or asks to work through queued/pending applications. Covers reading the JD Post, creating or updating the Agency/Client profile, and logging it in the Calendar — then hands off the actual sending to /apply-email or /apply-site depending on the channel.
---

# Apply to a pending job link

Everything here operates on career-mode's own database (events, agencies, clients) through its local API. This covers both cases: the user hands you one link directly, or you're clearing the queue of `pending` applications the sidebar's "Pending" page created.

## Reading and writing the data

Use the local API at `http://localhost:8333` (the interactive docs are at `/docs`; `./run-local.sh` starts the server if it isn't running). Send JSON with `curl -s -H 'Content-Type: application/json'`. The routes you need: `GET /api/agencies`, `GET /api/clients`, `GET /api/events` (filter with `?event=pending`, `?jdUrl=...`, `?agencyId=...`), `POST` to any of the three to create, `PATCH /api/<collection>/<id>` to change some fields, `DELETE /api/<collection>/<id>`. Never open the SQLite file directly: the API applies the rules below. Errors come back as `{"detail": "..."}`; a 409 means it already exists (name taken) or still has events.

## Hard rule: a Job Board Platform is read without the user's session, and only a JD Post

Never open a Job Board Platform (LinkedIn, Indeed, etc.) with Claude in Chrome or with anything signed in as the user: a platform can flag automated activity and restrict or disable the account. The browser is only for application forms on third-party sites (Workable, Viterbit, Loxo, the company's own ATS, etc.).

What a JD Post says is read from its **public page, with WebFetch** (it has no session, so nothing of the user's goes with it):

- A JD Post link, or a platform's short link (for example `lnkd.in`): fetch it. A short link answers with a redirect to the platform's own address: fetch that address again **without its query string** (tracking parameters like `?utm_source=...&rcm=...` can identify the user), only the path.
- Ask it for the JD Post's text: how to apply (an email address, a link, or only "send me a message"), the author, the company, the role, the requirements, the language and how long ago it was posted ("1w" is a week).
- Everything else on a Job Board Platform (profiles, company pages, feeds) is never fetched: its link is only **written down as given**, in `jdUrl`, in the event notes, in a profile's `linkedin` field.
- If the page gives no JD Post text (a login wall, an error, a deleted post), don't try another way in: ask the user to paste the JD Post's text and go on with that.

## The core process, for one link

1. Get the JD Post's details: what the user pasted, or else read the JD Post as the hard rule above says, and ask only for what is still missing: recruiter name, how to apply (an email to send the CV to, or a link), language, company, role, and the JD Post's **publication date**.
2. Check the JD Post is recent (**3 weeks max**) with its date. If it's older, flag that before going any further — it may no longer be active — and don't continue past this point without the user's confirmation. If there's no date, ask.
   Then **check the fit with the profile**: the JD Post's core requirements against the profile's roles and stack, what the user is not interested in, where they can work from and the salary range, when the JD Post states one. A clear mismatch (a main requirement the CV doesn't back, a stack or country the profile rules out) means don't apply: say why and leave the event pending. If it is borderline, ask. Never stretch the profile to fit a post.
   Then **decide the channel from what the JD Post says**, not from the link: an email address → `email_apply`; a link to a form or the company's site → `web_form` (set the pending event's `applyType` with a `PATCH`: the Pending page queues a link with no channel); neither, only "send me a message" → it can't be done by email: leave it pending and say so.
3. Pick the matching message from this app's Outreach → Messages tab (it shows `profile/outreach.md`): the **Application by Email Message** for a JD Post with an email, the **Cover Letter Message** for a form. Fill in its `platform_recruiter`/`platform_post_id` placeholders. If the text is still the example's placeholder (the Messages tab shows a banner while that is so), don't use it: ask the user to write it first (`profile/README.md` explains how).
4. **New agency or new final client?** First look for an existing one **by name (ignoring case)** in `GET /api/agencies` / `GET /api/clients`; the server refuses a second one with the same name (409), so a duplicate can't be created by accident. If it exists, reuse its `id` as it is. Only if there's none, and the company is an agency/intermediary (staffing, consultancy, recruiting company), look it up (its own website, or a web search, for what it actually does; never its page on a Job Board Platform, and `linkedin` is only the URL the user gave, if any) and `POST /api/agencies` a real profile, not just a bare name: `name`, `type`, `website`, `linkedin`, `recruiters`, `applicationLink`, etc. The server makes the `id`. Same for a new final client: `POST /api/clients` with `name`, `viaAgencyId`, `website`, and whatever else is known. If the agency/client already exists, don't touch its profile — just link the application to it.
5. **Log the application in the Calendar** — `POST /api/events` with `date`, `event`, `agencyId`/`clientId` (from step 4), `notes` (recruiter, link to the JD Post, context for this outreach) and `jdUrl`. This step is never skipped. A few things that are easy to get backwards here:
   - The application link and the specific recruiter for *this* process always go on the event, never on the agency/client profile — those stay calendar-agnostic, reusable across every application to that company.
   - There is no company label to fill in: the calendar shows the agency's name (or the direct client's), derived from the links, and "Agency → Client" is composed live when an event has both. When an agency is juggling more than one client at once, link each event to the agency and to the right client.
   - If this becomes a Rejection later with no reason given, the notes default to "Other candidates." rather than "No reason given."
6. Any new event reactivates the agency, except a closing event (**Rejection, Red Flag, On-hold, Offer or Archive**), which archives it. The server does that when you create the event — you never set the status by hand, just create the event with the right `event` type.
7. When showing the message in chat, links inside the body (the JD Post, the user's website) go as clickable markdown, not plain text — even though Gmail auto-linkifies them on its own once sent.
8. **Then send it.** This is the one point where the two channels genuinely diverge, so it's broken out into its own skill rather than inlined here twice:
   - `applyType: 'email_apply'` (the JD Post gives an email address) → follow **`/apply-email`**.
   - `applyType: 'web_form'` (anything else) → follow **`/apply-site`**.

   Both expect the recipient/subject/body or the form's context already resolved by steps 1-7 above — this skill does the resolving, the other two just do the sending.

## Processing the whole pending queue ("Apply Bulk links")

The sidebar's "Pending" page doesn't apply to anything itself — it queues a JD Post link as an event with `event: 'pending'` (plus `jdUrl`, with no `applyType` yet: the skill sets it) and stops there. Only links are queued: the form refuses an email address alone. Nothing gets processed until the user says **"Apply Bulk links"** (or similar) in chat. When that happens:

1. `GET /api/events?event=pending` for every pending event, oldest first (the list comes newest first, so reverse it).
2. A `pending` event holds only a link, so for each one read the JD Post as the hard rule says (one at a time, with a short pause between them) and run the core process above (steps 1-7), then dispatch by the channel the JD Post showed (`applyType`) — `email_apply` to **`/apply-email`** (sent through the app, no browser), `web_form` to **`/apply-site`** (through the connected browser).
3. Once a link is actually applied to: `POST` the real event (`event: 'application'`, with the resolved `agencyId`/`clientId`/`notes` per steps 4-5 above, carrying over the pending event's `applyType` — the Weekly Report's "by mail"/"by platform" counts read it off the final `application` event, not the deleted pending one) and `DELETE` the `pending` placeholder. Don't just flip its `event` field — the pending event is a rough stand-in and the real one needs the fully resolved fields.
4. If a link can't be completed (captcha, recorded video, dead link, JD Post too old, etc.), leave its `pending` event as-is and flag it in the summary instead of deleting it.
5. Finish with a short summary in chat: how many went through, how many are still pending and why.

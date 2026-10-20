---
name: apply-pending
description: Apply to a job the user sends — a JD Post link from a Job Board Platform (LinkedIn, Indeed...), a recruiter message, or any other portal link — or process the whole queue when the user invokes /apply-pending with no link. Use this whenever the user pastes a JD Post link and asks to apply, forwards something from a recruiter, or asks to work through queued/pending applications. Covers reading the JD Post, creating or updating the Agency/Client profile and choosing the channel, then hands off the actual sending to /apply-email or /apply-site, and logs the application in the Calendar once it went out.
---

# Apply to a pending job link

Everything here operates on career-mode's own database (events, agencies, clients) through its local API. This covers both cases: the user hands you one link directly, or you're clearing the queue of `pending` applications the sidebar's "Pending" page created. **`/apply-pending` with no link is the second case:** the first thing to do is check the pending list in the API (`GET /api/events?event=pending`) and work through it, without asking whether to start — the command is the order.

## Reading and writing the data

Use the local API at `http://localhost:8333` (the interactive docs are at `/docs`; if a request can't connect, `./run-local.sh` starts the server). Send JSON with `curl -s -H 'Content-Type: application/json'`. The routes you need: `GET /api/agencies`, `GET /api/clients`, `GET /api/events` (filter with `?event=pending`, `?jdUrl=...`, `?agencyId=...`), `POST` to any of the three to create, `PATCH /api/<collection>/<id>` to change some fields, `DELETE /api/<collection>/<id>`. Never open the SQLite file directly: the API applies the rules below. Errors come back as `{"detail": "..."}`; a 409 means it already exists (name taken) or still has events.

## Rule: on a Job Board Platform only a JD Post is read, and only read

Reading a JD Post on a Job Board Platform (LinkedIn, Indeed, etc.) is fine, and that is all: its profiles, company pages, feeds and messages are never opened, and nothing is ever done on the platform (no Easy Apply, like, comment, connect or message). A platform can flag automated activity and restrict the user's account, so keep it to reading, one post at a time with a short pause between them. The browser is also for application forms on third-party sites (Workable, Viterbit, Loxo, the company's own ATS, etc.) and for reading any other page that WebFetch can't read (see the last point below).

How a JD Post is read:

1. **WebFetch first**, on the post's public page (no session, so nothing of the user's goes with it). A JD Post link, or a platform's short link (for example `lnkd.in`): fetch it. A short link answers with a redirect to the platform's own address: fetch that address again **without its query string** (tracking parameters like `?utm_source=...&rcm=...` can identify the user), only the path.
2. **If that gives no JD Post text** (a login wall, an error, a post that only renders in a browser), open that same post, still without its query string, with **Claude in Chrome** (`mcp__claude-in-chrome__*`, loaded in one ToolSearch call) in a new tab, read its text and close the tab. Only that page: no clicks, no scrolling through feeds, no following links to the author's profile or the company.
3. If the post still gives no text (it was deleted), ask the user to paste the JD Post's text and go on with that.

What to take from it: how to apply (an email address, a link, or only "send me a message"), the author, the company, the role, the requirements, the language and how long ago it was posted ("1w" is a week).

- Everything else on a Job Board Platform (profiles, company pages, feeds) is never fetched or opened: its link is only **written down as given**, in `jdUrl`, in the event notes, in a profile's `linkedin` field.
- **When stuck on any other page** (a company's careers page, an ATS, a recruiter's own site: WebFetch returns nothing, an app that only renders in a browser, a login wall, a page that needs a click), open it with **Claude in Chrome** in a new tab and read it there, instead of stopping to ask the user. The user is not asked to paste what a browser can read.

## The core process, for one link

1. Get the JD Post's details: what the user pasted, or else read the JD Post as the hard rule above says, and ask only for what is still missing: recruiter name, how to apply (an email to send the CV to, or a link), language, company, role, and the JD Post's **publication date**.
   Then look the link up in the Calendar: `GET /api/events?jdUrl=<the link as given>` (it matches the text exactly, so if the link has a query string, look it up again without it). An existing `application` event means the user already applied to it: say so and stop, unless they tell you to apply again. An existing `pending` event is the queue's own placeholder for this link: step 6 replaces it.
2. Check the JD Post is recent (**3 weeks max**) with its date. If it's older, flag that before going any further — it may no longer be active — and don't continue past this point without the user's confirmation. If there's no date, ask.
   Then **check the fit with the profile**: the JD Post's core requirements against the profile's roles and stack, what the user is not interested in, where they can work from and the salary range, when the JD Post states one. A clear mismatch (a main requirement the CV doesn't back, a stack or country the profile rules out) means don't apply: say why and leave the event pending. If it is borderline, ask. Never stretch the profile to fit a post.
   Then **decide the channel from what the JD Post says**, not from the link: an email address → `email_apply`; a link to a form or the company's site → `web_form`; neither, only "send me a message" → it can't be done by email: leave it pending and say so. The Pending page only guesses the channel (every link it queues says `web_form`), so this decision is the one that counts.
3. Pick the matching message from this app's Outreach → Messages tab (it shows `profile/outreach.md`): the **Application by Email Message** for a JD Post with an email, the **Cover Letter Message** for a form. Use its text in the **JD Post's language** (if the profile has none in that language, ask). Fill in its placeholders: `platform_recruiter` is the recruiter's first name as the JD Post gives it (no name: ask), `platform_post_id` is the link to the JD Post. If the text is still the example's placeholder (the Messages tab shows a banner while that is so), don't use it: ask the user to write it first (`profile/README.md` explains how).
   For an email, also decide the **subject**: exactly what the JD Post asks for (a reference code, a format), or else the role and the user's full name, in the message's language, such as "Application for <role> – <full name>".
4. **New agency or new final client?** First look for an existing one **by name (ignoring case)** in `GET /api/agencies` / `GET /api/clients`; the server refuses a second one with the same name (409), so a duplicate can't be created by accident. If it exists, reuse its `id` as it is. Only if there's none, and the company is an agency/intermediary (staffing, consultancy, recruiting company), look it up (its own website, or a web search, for what it actually does; never its page on a Job Board Platform, and `linkedin` is only the URL the user gave, if any) and `POST /api/agencies` a real profile, not just a bare name: `name`, `type`, `website`, `linkedin`, `recruiters`, `applicationLink`, etc. The server makes the `id`. Same for a new final client: `POST /api/clients` with `name`, `viaAgencyId`, `website`, and whatever else is known. If the agency/client already exists, don't touch its profile — just link the application to it.
5. **Send it.** This is the one point where the two channels genuinely diverge, so it's broken out into its own skill rather than inlined here twice:
   - `email_apply` (the JD Post gives an email address) → follow **`/apply-email`**, with the recipient, the subject and the message from steps 1-3.
   - `web_form` → follow **`/apply-site`**.

   Both report back: sent or submitted, or stopped and why. If nothing went out (a captcha, a failed send, a dead link), don't log anything: leave the `pending` event as it is, if there is one, and say why. If the user finishes the form by hand and tells you so, go on to step 6.
6. **Log the application in the Calendar**, once it went out — `POST /api/events` with `date` (today), `event: 'application'`, `agencyId`/`clientId` (from step 4), `notes`, `jdUrl` and `applyType` (the channel of step 2: the Weekly Report's "by mail"/"by platform" counts read it off the `application` event). It is never skipped for an application that was sent. If a `pending` event for this link exists, `DELETE` it now: don't flip its `event` field, the pending event is a rough stand-in and the real one needs the fully resolved fields. A few things that are easy to get backwards here:
   - The application link and the specific recruiter for *this* process always go on the event, never on the agency/client profile — those stay calendar-agnostic, reusable across every application to that company. `notes` has the recruiter, the JD Post's link, the address or form it went to, and the context of this outreach.
   - There is no company label to fill in: the calendar shows the agency's name (or the direct client's), derived from the links, and "Agency → Client" is composed live when an event has both. When an agency is juggling more than one client at once, link each event to the agency and to the right client.
   - If this becomes a Rejection later with no reason given, the notes default to "Other candidates." rather than "No reason given."
   - Any new event reactivates the agency, except a closing event (**Rejection, Red Flag, On-hold, Offer or Archive**), which archives it. The server does that when you create the event — you never set the status by hand, just create the event with the right `event` type.

## Processing the whole pending queue

The sidebar's "Pending" page doesn't apply to anything itself — it queues a JD Post link as an event with `event: 'pending'` and `jdUrl`, and stops there. Only links are queued: the form refuses an email address alone. Nothing gets processed until the user invokes `/apply-pending`. When that happens:

1. `GET /api/events?event=pending` for every pending event, oldest first (the list comes newest first, so reverse it).
2. A `pending` event holds only a link, so for each one, one at a time with a short pause between them, run the core process above (read the JD Post as the hard rule says, then steps 1-6). Step 6 replaces the pending placeholder with the real `application` event.
3. If a link can't be completed (captcha, recorded video, dead link, JD Post too old, no fit, etc.), its `pending` event stays as it is and is flagged in the summary instead of being deleted.
4. Finish with a short summary in chat: how many went through, how many are still pending and why.

---
name: reply
description: Draft the user's reply to a recruiter who wrote first (a "passive contact", on a platform or by email) from the Proposal Reply Message, and log the contact in the Calendar. With --short, the message as it is; otherwise the same message adapted to answer what the recruiter asked. Use whenever the user pastes a recruiter's message, says "a recruiter wrote to me" or "reply that I'm interested", or invokes /reply.
model: sonnet
---

# Reply to a recruiter

The user pastes a message from a recruiter who wrote first (and maybe their profile link). Draft the reply, log it in the Calendar, done. The user sends the reply. Not for JD Posts the user applies to: those are `/apply-pending`'s.

**Never open the platform** (LinkedIn, etc.), with no tool: links to it are only written down as given. A JD on the company's own site, or the company's website, can be read with WebFetch.

## 1. The reply

Always start from the **📝 Proposal Reply Message** in `profile/outreach.md`, in the language of the recruiter's message (or the one the user asks for), with the recruiter's first name and the role filled in. Never write the reply from scratch, even when the user asks for it shorter or more casual: trim the template instead. If it's still the example's placeholder, ask the user to write it first (`profile/README.md` explains how).

What the recruiter asks (English level, CV, availability...) is **always** answered, in one short line, in both modes. Something the profile can't answer: ask the user. The CV is never attached, even when they ask for it attached: give the direct link from `profile/profile.md` (Basics → Website / CV, the `/cv` one), so the user attaches nothing and a recruiter who writes back about it is a real person.

- **`--short`:** the template plus only those answers.
- **Default:** also, for the technologies they name, only those, each with what `profile/profile.md` backs (years, where). A technology the profile doesn't cover is left out and mentioned to the user.

**It must not sound written by an AI.** Whatever is added sounds like the template around it, as the user would type it: plain, short sentences, no lists, no em dashes, no buzzwords or flattery ("excited", "passionate", "leverage", "I'd love to"), and no echoing the recruiter's phrasing back.

The salary and the email come from `profile/profile.md` at run time (Work preferences, Basics), not from memory. For a local role (an employee in the user's country, paid in local currency, or a recruiter asking for a gross monthly figure), use the local figure, drop the contractor (USD) clause and say "net".

Show the reply as a copyable block. Before it, at most three lines: the company (agency or direct employer, from its website), the terms, and any red flag (not remote, local pay well under the range, unpaid test, closed JD). If it's to say no, write a short polite decline instead.

## 2. The Calendar

Through the API at `http://localhost:8333` (`./start.sh` if it doesn't answer), with `curl -s -H 'Content-Type: application/json'`:

1. **Company:** find it in `GET /api/companies`, or `POST` it (`name`, `companyType` `agency`, or `client` for a direct employer, `website`, a one-line `notes` of what it does, `applicationLink` the JD link when the message gives one). An existing company gets the JD link as `applicationLink` when it has none, and the recruiter's profile link added to its `recruiters` (`PATCH /api/companies/<id>`; `recruiters` takes the full list).
2. **Event, one per conversation:** `GET '/api/events?companyId=<id>'`. A `passive_message` from the same recruiter in the last 7 days is the same thread: `PATCH` its `notes` with a new paragraph for this message (nothing if it's the same message). Otherwise `POST /api/events` with `event: 'passive_message'`, today's `date`, the `companyId`, `jdUrl` when the message gives a JD link (also `PATCH` it onto an existing event that lacks it), and `notes`: the recruiter (name, title, link), the role and JD link, the terms, what they asked and what the reply says (salary given, English level, CV).

Then show the draft. Say what was saved only if something failed. Nothing is sent and nothing is committed.

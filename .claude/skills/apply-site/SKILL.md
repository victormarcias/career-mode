---
name: apply-site
description: Fill out and submit a company's own application form on a third-party portal (Workable, Viterbit, Loxo, Ashby, Greenhouse, the company's own ATS, etc.) instead of sending an email. Use this whenever the user asks to apply through a company's portal/form or shares a link to one, including as the delivery step for /apply-pending when a JD Post's `applyType` is `web_form`.
---

# Apply on a company's portal/form

Open the form's link in a new tab of the connected Chrome and leave the user's other tabs alone. If the form **has no captcha** and needs no account, fill it out and submit it directly, without asking for confirmation field by field:

1. CV: use the file of the `CV_PDF_PATH` setting (`curl -s http://localhost:8333/api/settings/env`, the entry with that name), straight from where it is. If it is not set, say so and stop: the user sets it in Settings, or by running `/setup` again. Never look for a CV anywhere else.
2. Fill in without asking, since this is public/known data, all of it from the profile's Basics: name, birthdate, email, phone (the portal-friendly format if the form rejects spaces), LinkedIn, GitHub, website and location.
   Any other question (roles, stack, compensation, English level, work authorization, years of experience, a bio) is answered the way `/submit-profile` says, from the profile. If the profile has no answer for it (`(not set)`, or it doesn't cover the question), ask the user instead of guessing. A CV upload with no visible file input is handled as `/submit-profile` describes (never through the system file picker).
3. Cover letter / free-text field, if asked: adapt the **Cover Letter Message** (Outreach → Messages tab, which shows `profile/outreach.md`) to that specific posting's context — don't paste the generic one unmodified. If a required skill from the JD is weak or missing, say so honestly in that text rather than overstating it. If the text is still the example's placeholder (the Messages tab shows a banner while that is so), don't use it: ask the user to write it first (`profile/README.md` explains how).
4. Checkboxes: check "I accept the Terms"/Privacy Policy (required to submit). Never check a newsletter/"receive more offers"/"follow the company"/marketing opt-in — uncheck it if it comes pre-checked.
5. Captcha, or an account to create or a sign-in the user has not got open already: stop and flag it, leave the rest for the user to finish. Never create an account for them and never type a password.
6. A Loom-style pitch video demanded just to submit the application is a cancel — flag it and stop, same as a captcha. A formal AI-interview screening tool (camera-on, verbal Q&A, anti-cheat) at a later stage of a process already moving forward is a different thing — still flag it since it's a judgment call, but lean toward it being fine rather than an automatic cancel.
7. Submit directly, no confirmation needed. Reasons worth actually stopping for are real red flags (not remote, salary far off from the profile's range, missing a hard requirement) — not a routine "should I send this?" check.
8. Check that it went through: a confirmation message or page, not a form that came back with errors. Fix a validation error you can fix (a phone format, a required field the profile answers); anything else is flagged.

**When stuck** (a captcha, a sign-in, a click or a field you can't do, a step you don't understand), don't close anything or give up on the page: leave the form open in Claude in Chrome with everything you could fill in, bring that tab to the front, and tell the user exactly what is left to click or type. They do it themselves; when they say it is done, check the confirmation (step 8) and report it as submitted.

**Report back** to the caller: submitted (with what the confirmation said), or stopped and why (captcha, account, video, red flag, a question the profile doesn't answer). `/apply-pending` logs the application in the Calendar only when it went out, so a form left half-filled is reported as stopped, never as done.

This is the delivery step only — if a new Agency/Client needs a profile or the application needs to be logged in the Calendar, that's `/apply-pending`'s job, not this one's.

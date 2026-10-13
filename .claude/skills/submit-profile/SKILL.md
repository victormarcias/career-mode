---
name: submit-profile
description: The user's candidate profile as a quick reference, read from `profile/profile.md` — for filling candidate-portal wizards and profile builders ("LinkedIn clones" like Mira, Torre, Flexhire) and any application form that asks for roles, stack, compensation, English level, experience or a bio. Use this whenever filling out such a form, and check the profile's known-portals list before building a profile from scratch on a new portal.
---

# Clone the profile

The data lives in `profile/profile.md` — the user's own file, gitignored, started from `profile/profile.example.md` (`profile/README.md` explains how to fill it from a CV). Read it at run time instead of working from memory, so a change there flows through, and never copy any of it into a tracked file. Its **Rules for presenting me** section, when it has any (it is optional), always applies. A field that says `(not set)` has no answer yet: ask the user for it when a form needs it, offer to save it in `profile/profile.md`, and never guess it or use the example person's value.

## Using it

- **Basics:** name, contact, links, CV and photo. When a form has a CV/resume upload, upload the file of the `CV_PDF_PATH` setting (`curl -s http://localhost:8333/api/settings/env`, the entry with that name), even if the field is marked optional. If it is not set, say so and stop: the user sets it in Settings, or by running `/setup` again. Never look for a CV anywhere else. If a portal shows no file input until you press its upload button (Indeed's "Choose from library"), press it, then look for the `type=file` input that appeared in the page and give it the file with the browser tool's file upload; never click through the system file picker, which can't be driven. Same for a profile-picture upload, with `profile/photo.*` (the picture uploaded in Settings; an older profile may have a photo link instead); with neither, say the user has to upload it in Settings (crop or center on the face if the form has a cropper).
- **Roles and stack, in priority order:** when a form limits how many you can pick, fill them in the order the profile lists them. With no limit, the whole must-have list applies.
- **Not interested:** skip what the profile lists even if a form suggests it as a match.
- **Everything else** is fair game only if it matches the actual CV: never add a role or a technology just because a form offers it.
- **Work preferences:** where to work from, position type, work shift (pick "Anytime"/flexible if a form allows only one option).
- **Compensation:** answer from the profile when a form has a compensation field; if it has none, don't volunteer it, since that is negotiated per opportunity. The expected salary range for emails and recruiter replies is its own line in the profile.
- **Self-assessment** (English level, areas of expertise, technologies known best): take the answers from the profile and cross-check them against the CV; don't pad the list with technologies a role's own "Tech:" line doesn't name. Portals that ask for one number of years per skill use the profile's "years per skill" list, which takes precedence over the brackets.
- **Profile or experience pages** (photo, work history, repos): copy each role from the CV in reverse-chronological order, the CV's bullets verbatim and each role's technologies from its own "Tech:" line only. Technical tests and certifications are left to the user.
- **Known portals:** the profile lists the candidate portals where a full profile is already built. Check it before starting from scratch on one: if it is there, update the existing profile instead of duplicating it. When a new portal turns out to be a full profile builder, add it to the list in the profile.
- **Bio:** use the short bio for a free-text "about you" field.

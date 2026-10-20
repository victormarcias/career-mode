# apply-site

Fills in and submits a job application on a company's own portal or web form (Workable, Viterbit, Loxo, a custom ATS). It's the delivery step for applications whose `applyType` is `web_form`.

- **Does:** uses the CV file (`CV_PDF_PATH` setting), fills the known public data from `profile/profile.md`, adapts the Cover Letter Message for any cover-letter field, accepts only the required terms, leaves marketing opt-ins unchecked, and submits without asking.
- **Stops and flags:** captchas, accounts to create, Loom-style pitch videos demanded just to apply, and questions the profile doesn't answer (it asks instead of guessing). Other questions are answered straight from the profile; a portal that wants a whole profile built is [submit-profile](../submit-profile/README.md)'s.
- **When stuck:** leaves the form open in Chrome, filled as far as it got, in front, and says exactly what is left for the user to click or type; it carries on when they say it is done.
- **Reports back:** submitted (once the confirmation shows) or stopped and why, so the caller logs the application only when it went out.
- **Touches:** the connected Chrome session (the Google account named in the profile). Nothing in the database.
- **Called by:** [apply-pending](../apply-pending/README.md), which also logs the application and creates any new agency or client.

Instructions: [SKILL.md](SKILL.md).

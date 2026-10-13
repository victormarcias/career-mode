# apply-site

Fills in and submits a job application on a company's own portal or web form (Workable, Viterbit, Loxo, a custom ATS). It's the delivery step for applications whose `applyType` is `web_form`.

- **Does:** uses the CV file (`CV_PDF_PATH` setting), fills the known public data from `profile/profile.md`, adapts the Cover Letter Message for any cover-letter field, accepts only the required terms, leaves marketing opt-ins unchecked, and submits without asking.
- **Stops and flags:** captchas, and Loom-style pitch videos demanded just to apply.
- **Touches:** the connected Chrome session (the Google account named in the profile). Nothing in the database.
- **Called by:** [apply-pending](../apply-pending/README.md), which also logs the application and creates any new agency or client.

Instructions: [SKILL.md](SKILL.md).

# apply-site

Fills in and submits a job application on a company's own portal or form
(Workable, Viterbit, Loxo, a custom ATS). It is the delivery step for
applications whose `applyType` is `web_form`, called by
[apply-pending](../apply-pending/README.md), which also logs the application.

It uses the CV file of the `CV_PDF_PATH` setting and the public data and open
answers from `profile/profile.md`, accepts only the required terms and submits
without asking. On a captcha, an account to create, a pitch video or an AI
interview it stops, leaves the form open in Chrome filled as far as it got, and
says what is left for the user. It reports submitted, or stopped and why. It
touches only the connected Chrome session, nothing in the database.
Instructions: [SKILL.md](SKILL.md).

# apply-pending

Applies to a job link end to end, or clears the whole queue of `pending`
applications that the app's Pending page collects, when `/apply-pending` runs
with no link. For each link it reads the JD Post, checks that it is recent (not
updated a month ago or more) and that the profile fits (Python or JavaScript is
what counts, other tools can be learned, AI roles always apply), chooses email
or web form from what the post says, fills the matching message and creates the
company when it is new.

The sending goes to [apply-email](../apply-email/README.md) or
[apply-site](../apply-site/README.md), and the application is logged in the
Calendar only once it went out; a link that cannot be finished stays pending,
and the run shows a table of what was and was not applied to. It touches the
career-mode database through its local API and, for forms and pages WebFetch
cannot read, the connected Chrome. On a Job Board Platform only a JD Post is
read, never profiles, company pages or feeds. Instructions:
[SKILL.md](SKILL.md).

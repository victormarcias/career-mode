# read-cv

Reads the user's CV (a PDF file or a link to one) and fills the CV-derived parts
of `profile/profile.md`: education, the total years and every role with its
dates, its own "Tech:" line and its bullets word for word. The first time it
also fills the name, contact details, links, a draft bio and the years per
technology, and asks in one numbered message for the decisions that are the
user's own, any of which can be skipped and is then written as `(not set)`.

It shows a before and after and waits for the OK, backs up the current profile
in `profile/backups/` and writes only `profile/profile.md`. Run it as `/read-cv
<path or link>` the first time and whenever the CV changes; with no argument it
reads the file of the `CV_PDF_PATH` setting. Instructions: [SKILL.md](SKILL.md).

# go-hunting

Goes through the job boards of the platforms where the user already has a
profile (the "Job Board Sites" of `profile/profile.md`), checks each platform
allows applying with AI, reads the recent jobs and their details, and applies
to the ones that fit the profile with flexible criteria (the language counts,
a tool or a seniority never rules a job out), answering the application
questions as `/apply-site` does. Each application is logged in the Calendar.

It keeps a record of each platform in `profile/job_boards.md` (gitignored):
the jobs page, whether AI is allowed, the date of the last hunt and notes on
how the board works. It asks for a platform's jobs page only when that
platform has no record yet, all of them in one question, and never again.
LinkedIn's job search is never crawled. It never pays credits or Connects,
never signs in and never solves a captcha: those are left to the user, listed
in the final table. `/go-hunting <platform>` runs only that platform.
Instructions: [SKILL.md](SKILL.md).

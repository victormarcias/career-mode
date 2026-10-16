# commit

Commits the current changes the way the user wants them: short and under their own name.

- **Does:** looks at the branch and the status, stages only the files that belong to the change (by explicit path), and commits on the branch that is already checked out with a one-line message in the style of the repo's history.
- **Never:** creates or switches a branch, sets an author other than the default one, adds a `Co-Authored-By` or any attribution line, amends, skips hooks or pushes.
- **Touches:** the local git repository only. It stops if anything personal (`profile/`, `data/`, `backup/`, `.env`) shows up in the change.
- **Use it:** `/commit`, or just say "commit" (and, if you want, what to commit and the message).

Instructions: [SKILL.md](SKILL.md).

# commit

Commits the current changes the way the user wants them: short and under their own name.

- **Does:** looks at the branch and the status, stages only the files that belong to the change (by explicit path), and commits on the branch that is already checked out with a one-line message in the style of the repo's history.
- **Never:** commits on its own (only when you run it, so you read the diff first), creates or switches a branch, sets an author other than the default one, adds a `Co-Authored-By` or any attribution line, amends, skips hooks or pushes.
- **Touches:** the local git repository only. It checks status and stops for staged or untracked personal data under `profile/`, `data/`, `backup/` or `.env`, while allowing the tracked `profile/README.md` and `profile/*.example.*` exceptions in `CLAUDE.md`.
- **Use it:** `/commit` (and, if you want, what to commit and the message), after you have looked at the diff.

Instructions: [SKILL.md](SKILL.md).

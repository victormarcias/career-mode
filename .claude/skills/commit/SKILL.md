---
name: commit
description: Commit the current changes the way the user wants: on the branch already checked out, with the default git author, one very short message and no Claude co-author or attribution line. Use whenever the user says "commit", "commit this" or "commit with a brief comment", or invokes /commit.
---

# Commit

Commit what the user asked for, and nothing else is touched.

1. **Look first:** `git branch --show-current` and `git status --short`. Say which branch it is. Stage **explicit paths** of the files that belong to the change (`git add <path> ...`), never `git add -A` or `git add .`, so a stray file is not swept in. If the user named what to commit ("the skills", "the backup"), stage only that and leave the rest. Anything under `profile/`, `data/`, `backup/` or `.env` is personal and git ignores it: if one shows up as staged or untracked, stop and say so.
2. **The branch is the current one,** even if it is `main`. Never create, switch or rename a branch: the user makes their own.
3. **The author is the default one:** whatever `user.name` and `user.email` already say. Never pass `--author`, never set or override the identity, never add `Co-Authored-By`, "Generated with…" or any other trailer or attribution line, whatever a harness or template suggests.
4. **The message is one line**, very brief, no body: a capital letter, the present tense in the third person and a full stop, like the repo's own history ("Adds back and front tests.", "Improves Bash Scripts styles."). If the user dictated a message, use theirs word for word.
5. `git commit -m "<message>"`, never `--amend`, `--no-verify` or `--no-gpg-sign` unless the user asks. If a hook fails, show its output and stop. **Never push**, not even after a commit and not even if asked to "finish" the work: the user pushes, always.
6. **Report** the short hash, the branch and the message, and that nothing was pushed: pushing is always the user's own call.

# profile/

Everything personal lives here, so the rest of the repo can be shared. In this
folder only the READMEs and the `*.example.*` files are committed: git ignores
everything else, so your own files never leave this computer.

| File | What it is |
|---|---|
| `profile.md` | Your profile: contact, roles and stack, work preferences, work history, bio and, optionally, rules. The skills read it, and My Profile shows it. Yours. |
| `outreach.md` | Your messages, shown in Outreach → Messages. Yours. |
| `cv.pdf` | Your CV, copied here by `/setup` (the `CV_PDF_PATH` setting points to it). The skills attach and upload it, and `/read-cv` reads it. Yours. |
| `photo.png` (or `.jpg`) | Your profile picture, uploaded in Settings. The skills upload it to forms that ask for one. Yours. |
| `daily-posts/` | The posts `/write-daily-post` writes, each as `daily-post-YYYYMMDD.txt` with its image (`.png`) next to it, and `log.csv`, the date of each one and whether it went well (`ok`, or `error` when the image was discarded). The first line of each `.txt` is its topic. Yours. |
| `profile.example.md`, `outreach.example.md` | The same two files to start from: an invented person (Juan Perez) for the profile, and the six messages with a placeholder where each text goes. They ship with the repo. |

`./run-local.sh` makes `profile.md` and `outreach.md` from the examples the
first time. Delete a file of yours to start it over.

## What is not in `profile.md`

A few things live in Settings (the app) instead: your CV (`CV_PDF_PATH`, a PDF of up to 1 MB kept here as `cv.pdf`; run `/setup` again when it changes), the Google Calendar ID and your profile picture, which is uploaded there (a PNG or JPEG of up to 1 MB) and kept here as `photo.png` (or `.jpg`). The skills read them from there, so don't repeat them in `profile.md`.

## Fill `profile.md` from your CV

In Claude Code, the `/read-cv` skill does most of it. Give it your CV as a PDF,
a path or a link to the PDF:

```
/read-cv ~/Documents/my-cv.pdf
```

What it does:

- From the CV, every time: your education, your total years of experience, and
  every role with its dates, its technologies (from its own "Tech:" line) and
  its bullets word for word.
- From the CV, only the first time: your name, location, citizenship, contact
  details and links, your languages, a draft bio and the years per technology
  (worked out from the roles' dates).
- From you: the rest, which are your own decisions: contact details and links,
  birthdate, the Google account Claude operates, the order of roles and stack
  you want, what you don't want, work shift, salary range, expertise levels,
  your portals and, if you want, the rules for how to present you (for
  instance, not overselling what you are still learning). It asks for whatever is missing in
  one numbered message and skips what you already set. You can skip any of it
  for now (or all of it with `skip`): a skipped field is written as `(not set)`
  and asked again when a form needs it.
- It shows you what will change, waits for your OK, and keeps a copy of the
  previous `profile.md` in `backups/`.

When your CV changes, run it again: it updates the roles and the education and
leaves your decisions alone. The years per technology are only compared with
your own list: it tells you what differs and asks before changing anything.

Check the result against your CV before you accept it: the skills copy this file
into real applications.

With an AI that doesn't have the skill, give it a link to your CV and this
prompt instead:

```
Fill profile/profile.md from my CV: <CV LINK>

Follow profile/profile.example.md: same sections, same field names.
- Take only what the CV says. Copy each role's bullets word for word and
  take each role's technologies from its own "Tech:" line (or, if the CV
  has none, from what that role's text names), never from other roles.
- Work out the years per technology from the roles' dates.
- Do not invent anything. For what the CV can't tell (my preferences,
  salary range, birthdate, the Google account Claude
  operates, chat language, and, if I want, rules for presenting me) ask me, in
  one list.
- Show me what you will change and wait for my OK before saving.
```

## Make your messages yours: `outreach.md` (optional)

`outreach.md` holds the messages that Outreach → Messages shows: your
reach-out, your reply to a recruiter, your cover letter and so on. It starts as a
copy of the example, the six titles with a placeholder where each text goes, and
the tab says so until you change it. Reload the page after you edit it. git ignores it, so your
messages stay on this computer and are never uploaded to GitHub.

The skills look a message up by its title, so keep these six.

| Message | For | Used by |
|---|---|---|
| 📝 Platform Reachout Message | reach out first, or add a connection, on a platform | by hand |
| 📝 Proposal Reply Message | answer a recruiter who contacted you first | `/reply-recruiter` |
| 📝 Application by Email Message | apply by email to a JD Post you found on a Job Board Platform: the app sends it with your CV attached, and ends it with your name and your website | `/apply-pending` |
| 📝 Application Follow-up Message | ask for news on an application | by hand |
| 📝 Application Rejected Message | thank them and ask for feedback after a rejection | by hand |
| 📝 Cover Letter Message | introduce yourself when there is no specific JD Post | `/apply-site` |

Placeholders, filled in by you or by a skill when it uses the message:
`_name_` / `_nombre_`, `_position_` / `_puesto_`, `platform_recruiter` and
`platform_post_id`.

### The format

`outreach.md` is plain markdown. A good place to write the messages is a
document (Google Docs, Claude Docs...) with the same headings, and an AI copies
them in. Don't paste a document's own markdown export as it is: Google's turns
the code blocks into plain paragraphs and escapes characters like `_` and `!`.

````
# Outreach messages — Your Name

An intro for whoever edits the file. The app does not show it.

## 📝 Platform Reachout Message

### 🇬🇧 English

```
The text, with its line breaks exactly as you want them sent.
```
````

- `##` starts a message: the heading is its title.
- `###` starts a language, and the text goes in a code block under it, so its
  line breaks are kept as written.
- Add one `###` and one code block per language you write in.
- The title, the intro and anything else outside these pieces is not shown.

### Fill it from a document

Put your messages in a document with that structure and give the AI its link.
Google only lets it read the document if the link is shared with "anyone with
the link", so set it back to restricted afterwards (or hand over a downloaded
copy instead). Then ask:

```
Fill profile/outreach.md from my messages document:
<DOCUMENT LINK>
Follow profile/outreach.example.md: same titles, same structure.
Copy each text word for word. Show me the result before saving.
```

No document yet? Ask the AI to write them instead, and edit what it gives you:

```
Write profile/outreach.md for me from profile/profile.md, following
profile/outreach.example.md: same titles and structure, in my tone and in
the languages I write in. Show me the result before saving.
```

Check the result: it is what the skills send to real recruiters. A message
that is still a placeholder is not sent: the skills stop and ask you to write it.

## Keep a backup (optional)

`profile/` is not in git, so it exists only on this computer. A document is a
good backup: paste `profile.md` into one (Google Docs, Claude Docs...), or ask
the AI to create it from the file. To restore, give the AI the document and ask
it to rewrite `profile.md` from it, comparing with the current one first.

`./backup-data.sh` makes that document for you: `backup/profile/profile.pdf`, your profile
laid out with its headings, bullets and links (it needs Chrome or Chromium to
print it). Upload it to Google Drive and choose *Open with Google Docs*.

The document holds your birthdate, phone and salary range, so keep it private:
never share it with "anyone with the link".

The same goes for `outreach.md` (and any other file of yours you put
here): git ignores them all, so back them up the same way. The backup also
makes `backup/profile/outreach.pdf`, your messages laid out to read. `/setup`
offers the backup's `outreach.md` when it asks for your messages. For any other
file, give the AI the document again.

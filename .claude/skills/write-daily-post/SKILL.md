---
name: write-daily-post
description: Generate the user's daily LinkedIn-style reflection post, grounded in a topic file from the notes folder named in `profile/profile.md`, plus an optional accompanying image. Use this whenever the user asks for their "daily post" or "today's post", even in short, casual asks. Also use it for a later, separate ask to generate the accompanying image for a post already shown in chat.
---

# Daily Post (reflection)

The user writes a short daily reflection post for social media (LinkedIn-style), grounded in whatever they've been reading in their notes folder — the one named under "Notes folder" in `profile/profile.md` (a personal collection of topic notes, organized by category, usually a sibling repo). The post reads like a real senior engineer's take, not a summary of the notes. Follow the profile's "Rules for presenting me" here too: never overstate what the user is still learning.

## 1. Pick a topic file

If the user names a topic, use the note that covers it (and say which). Otherwise pick any `.md` file from the notes folder (a path relative to this repo, as the profile gives it), from any of its categories (its sub-folders). No category is preferred over another — but favor variety across categories over time rather than defaulting to the same one repeatedly. If the profile names no notes folder, ask the user which one to use.

The topics already posted about are the `Topic:` first line of each post saved in `profile/daily-posts/` (step 4), each as `<note>/<specific point>`, such as `dom-events/preventDefault`, and `log.csv` says which of them went well. Read both before choosing (`grep -m1 '^Topic:' profile/daily-posts/*.txt`, if there are any). Don't pick a note or a point that is already there while unused ones remain (a note holds several points, so one already used can be taken again for a different point), and prefer the categories (look a note's up in the notes folder) that appear least or longest ago. A post whose log status is `error` was never published: its topic does not count as used, and it is the first to reuse. If the user says a topic was used recently that the files don't show, pick a different one.

## 2. Write the reflection

One single paragraph, written as a senior developer thinking out loud — not a summary of the topic file, a *take* on it. Ground it in the file's actual content and specifics (the real trade-offs, terms, and examples it names), not generic filler or textbook-sounding prose. Tone: optimistic, with a light touch of wit — wit is a seasoning here, not the main flavor, so don't force a joke into every sentence. Plain, direct language, no buzzword soup ("leverage", "synergy", "paradigm shift", etc.). Always write it in English, for broad social reach regardless of what language the user asked in.

## 3. Add hashtags

List 5–10 hashtags below the paragraph: a mix of ones specific to the topic (e.g. `#n8n`, `#LangChain`) and broader software/career ones (e.g. `#SoftwareEngineering`, `#TechCareers`).

## 4. Show it and save it

Show the post and hashtags directly in chat: that's the deliverable. The user copies it and posts it themselves — never post it anywhere automatically (no LinkedIn automation, no drafting through any social API).

Also save it in `profile/daily-posts/` (create the folder; git ignores `profile/`, so it stays on this computer) as `<name>.txt`, which holds, in this order: a first line `Topic: <note>/<specific point>`, a blank line, the paragraph, a blank line and the hashtags. The topic is the note's name without its extension, a slash and the specific point the post is about, short and in the note's own terms, such as `Topic: dom-events/preventDefault`: a note holds several points, so it is more specific than the note. `<name>` is `daily-post-YYYYMMDD`, today's date, with no topic in it; add `-2`, `-3`... if that name is taken, and never overwrite a file. The image of step 5 starts with the same name.

Then add one line to `profile/daily-posts/log.csv`, which only says whether each post went well: `date,status`, with the date exactly as the file name has it after `daily-post-` (`YYYYMMDD`, or `YYYYMMDD-2`...) and the status `ok`. Create the file with the header line `date,status` if it is not there, and only append lines (the one exception is marking a line `error`, as step 5 says). One line per post, even if two share a day. Save nothing anywhere else: that folder is the only place the posts and their log go.

## 5. If asked for the accompanying image

Only do this if the user separately asks for it (in the same turn or a later one) — don't generate it by default.

1. Check the key is set: `GEMINI_API_KEY` in `curl -s http://localhost:8333/api/settings/env` (`isSet`). If it is not, say so and stop: the user sets it in Settings, or by running `/setup` again.
2. The image is named like the post it belongs to: `profile/daily-posts/<name>.png`, with the `<name>` of the `.txt` saved in step 4 for the post shown in chat. If that image filename is taken, append `-2`, `-3` and subsequent numeric suffixes until free; never overwrite an earlier image. Keep track of the exact image paths for cleanup. If that post was never saved (it is from before this folder), save its `.txt` first, as in step 4.
3. Make a temporary directory outside this repo (`mktemp -d`) and write the post's paragraph text (just the reflection, no hashtags needed) to a plain text file in it.
4. Run `scripts/generate_daily_image.py <post_text_file> <chosen_image_path>` from this repo’s root, using the unused image path selected in step 2. It calls the Gemini API (reading `GEMINI_API_KEY` from this repo's own `.env`, gitignored) and prints the path of the image it wrote. If it fails (including either request or subprocess timeout, an API error, or a response with no image), show the error, delete the temporary directory and any image from this run, apply the publication-aware log rule below and stop without saving an image or retrying. Keep the existing post text.
5. Copy the image to `~/Downloads` too (without overwriting a file there) — the user expects to find it there — and delete the temporary directory.
6. Deliver it to the user as a downloadable attachment (`display: "attach"`) — never render it inline, since it's meant to be saved and uploaded elsewhere, not looked at in the chat panel. In the same reply, show the post's text again in chat, the paragraph and the hashtags exactly as saved in the `.txt` (without its `Topic:` line), so the user can copy the text and take the image from the same place.

**A bad image is discarded.** When a run fails, or the user says the image came out wrong, determine whether the text was published before changing `log.csv`; ask if that is unknown and leave the row unchanged until answered. Only for an unpublished post, set its line to `error` (change that line only), so the topic is reused next time. Preserve a published post’s log status and topic history. In either case, delete only this run’s image from `profile/daily-posts/` and its copy in `~/Downloads`, and remove its temporary directory. The post’s `.txt` stays. Do not generate another image the same day unless the user asks.

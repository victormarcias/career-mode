---
name: write-daily-post
description: Generate the user's daily LinkedIn-style reflection post on the topic they give in the command (`/write-daily-post <topic>`), plus an optional accompanying image. Use this whenever the user asks for their "daily post" or "today's post", even in short, casual asks. Also use it for a later, separate ask to generate the accompanying image for a post already shown in chat.
---

# Daily Post (reflection)

The user writes a short daily reflection post for social media (LinkedIn-style) on a topic they give as the input of the command. The post reads like a real senior engineer's take, not a summary. Follow the profile's "Rules for presenting me" here too: never overstate what the user is still learning.

## 1. Take the topic

The topic is what the user wrote after the command (`/write-daily-post <topic>`, in any language), and nothing else: never pick one on your own and never read a notes folder. With no topic given, ask for one and stop.

Look at the posts already saved (`grep -m1 '^Topic:' profile/daily-posts/*.txt`, if there are any): when the user's topic is already there, say so in one line and take a different angle on it, instead of repeating the post.

## 2. Write the reflection

One single short paragraph, **at most about 90 words** (four or five sentences), written as a senior developer thinking out loud — not a summary of the topic, a *take* on it. Ground it in specifics (the real trade-offs, terms, and examples of the topic), not generic filler or textbook-sounding prose. Tone: optimistic, with a light touch of wit — wit is a seasoning here, not the main flavor, so don't force a joke into every sentence. One idea, no padding: cut any sentence that only repeats the previous one. No engagement bait ("comment YES if…") and no links in the paragraph, which LinkedIn pushes down. No emojis in the text unless the user asks for one, and then one at most, never repeated. Plain, direct language, no buzzword soup ("leverage", "synergy", "paradigm shift", etc.). Always write it in English, for broad social reach regardless of what language the user asked in.

## 3. Add hashtags

List 3–5 hashtags below the paragraph (hashtags weigh little on LinkedIn, and more than five reads as noise): a mix of ones specific to the topic (e.g. `#n8n`, `#LangChain`) and broader software/career ones (e.g. `#SoftwareEngineering`, `#TechCareers`).

## 4. Show it and save it

Show the post and hashtags directly in chat: that's the deliverable. The user copies it and posts it themselves — never post it anywhere automatically (no LinkedIn automation, no drafting through any social API).

Also save it in `profile/daily-posts/` (create the folder; git ignores `profile/`, so it stays on this computer) as `<name>.txt`, which holds, in this order: a first line `Topic: <area>/<specific point>`, a blank line, the paragraph, a blank line and the hashtags. The topic is a short area name, a slash and the specific point the post is about, in the user's own terms, such as `Topic: ai-content/dead internet and ai slop`. `<name>` is `daily-post-YYYYMMDD`, today's date, with no topic in it; add `-2`, `-3`... if that name is taken, and never overwrite a file. The image of step 5 takes the same name.

Then add one line to `profile/daily-posts/log.csv`, which only says whether each post went well: `date,status`, with the date exactly as the file name has it after `daily-post-` (`YYYYMMDD`, or `YYYYMMDD-2`...) and the status `ok`. Create the file with the header line `date,status` if it is not there, and only append lines (the one exception is marking a line `error`, as step 5 says). One line per post, even if two share a day. Save nothing anywhere else: that folder is the only place the posts and their log go.

## 5. If asked for the accompanying image

Only do this if the user separately asks for it (in the same turn or a later one) — don't generate it by default.

1. Check the key is set: `GEMINI_API_KEY` in `curl -s http://localhost:8333/api/settings/env` (`isSet`). If it is not, say so and stop: the user sets it in Settings, or by running `/setup` again.
2. The image is named like the post it belongs to: `profile/daily-posts/<name>.png`, with the `<name>` of the `.txt` saved in step 4 for the post shown in chat. If that post was never saved (it is from before this folder), save its `.txt` first, as in step 4.
3. Make a temporary directory outside this repo (`mktemp -d`) and write the post's paragraph text (just the reflection, no hashtags needed) to a plain text file in it.
4. Run `scripts/generate_daily_image.py <post_text_file> profile/daily-posts/<name>.png` from this repo's root. It calls the Gemini API (reading `GEMINI_API_KEY` from this repo's own `.env`, gitignored) and prints the path of the image it wrote. If it fails (an error, or Gemini answers with text and no image), say so in one line, delete nothing yet and **make the image yourself**, with no second try at Gemini: draw a 1080×1080 SVG in the temporary directory (the post's key sentence or two as large text on a plain dark background with one accent colour, nothing cut off or crowded), render it with `qlmanage -t -s 1080 -o <dir> <file>.svg` (macOS; it writes `<file>.svg.png`), open the PNG to check the text fits, and save it as `profile/daily-posts/<name>.png`.
5. Copy the image to `~/Downloads` too (without overwriting a file there) — the user expects to find it there — and delete the temporary directory.
6. Deliver it to the user as a downloadable attachment (`display: "attach"`) — never render it inline, since it's meant to be saved and uploaded elsewhere, not looked at in the chat panel. In the same reply, show the post's text again in chat, the paragraph and the hashtags exactly as saved in the `.txt` (without its `Topic:` line), so the user can copy the text and take the image from the same place.

**A bad image is discarded.** When the user says the image came out wrong, the post was not published: set the status of that post's line in `log.csv` to `error` (change that line only) and delete the image from `profile/daily-posts/` and the copy in `~/Downloads`. The post's `.txt` stays. Do not generate another image the same day unless the user asks.

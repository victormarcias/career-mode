---
name: write-daily-post
description: Generate the user's daily LinkedIn-style reflection post, grounded in a topic file from the notes folder named in `profile/profile.md`, plus an optional accompanying image. Use this whenever the user asks for their "daily post" or "today's post", even in short, casual asks. Also use it for a later, separate ask to generate the accompanying image for a post already shown in chat.
---

# Daily Post (reflection)

The user writes a short daily reflection post for social media (LinkedIn-style), grounded in whatever they've been reading in their notes folder — the one named under "Notes folder" in `profile/profile.md` (a personal collection of topic notes, organized by category, usually a sibling repo). The post reads like a real senior engineer's take, not a summary of the notes. Follow the profile's "Rules for presenting me" here too: never overstate what the user is still learning.

## 1. Pick a topic file

Pick any `.md` file from the notes folder (a path relative to this repo, as the profile gives it), from any of its categories (its sub-folders). No category is preferred over another — but favor variety across categories over time rather than defaulting to the same one repeatedly. If the profile names no notes folder, ask the user which one to use.

Nothing tracks which topics have already been posted about, anywhere — this was tried twice and explicitly reverted both times, so don't reintroduce a log or tracking file even if it seems like it would help. If a topic was already used recently, the user will just say so in chat, and you pick a different one. This is intentionally lightweight — a log file is more upkeep than it's worth for a one-person, low-stakes routine.

## 2. Write the reflection

One single paragraph, written as a senior developer thinking out loud — not a summary of the topic file, a *take* on it. Ground it in the file's actual content and specifics (the real trade-offs, terms, and examples it names), not generic filler or textbook-sounding prose. Tone: optimistic, with a light touch of wit — wit is a seasoning here, not the main flavor, so don't force a joke into every sentence. Plain, direct language, no buzzword soup ("leverage", "synergy", "paradigm shift", etc.). Always write it in English, for broad social reach regardless of what language the user asked in.

## 3. Add hashtags

List 5–10 hashtags below the paragraph: a mix of ones specific to the topic (e.g. `#n8n`, `#LangChain`) and broader software/career ones (e.g. `#SoftwareEngineering`, `#TechCareers`).

## 4. Show it — don't post or save it

Show the post and hashtags directly in chat. That's the deliverable. The user copies it and posts it themselves — never post it anywhere automatically (no LinkedIn automation, no drafting through any social API). Don't save anything to any repo afterward: no log file, no draft file, nothing. This one's a hard, twice-confirmed decision — the whole point of this routine is that it leaves no trace.

## 5. If asked for the accompanying image

Only do this if the user separately asks for it (in the same turn or a later one) — don't generate it by default.

1. Check the key is set: `GEMINI_API_KEY` in `curl -s http://localhost:8333/api/settings/env` (`isSet`). If it is not, say so and stop: the user sets it in Settings, or by running `/setup` again.
2. Make a temporary directory outside this repo (`mktemp -d`) and write the post's paragraph text (just the reflection, no hashtags needed) to a plain text file in it.
3. Run `scripts/generate_daily_image.py <post_text_file> <temp_dir>/daily-post-image.png` from this repo's root. It calls the Gemini API (reading `GEMINI_API_KEY` from this repo's own `.env`, gitignored) and prints the path of the image it wrote. If it fails, show its error and stop; don't retry in a loop.
4. Copy the resulting image to `~/Downloads` — always, even if you already wrote it to a temp/scratch path. The user expects to find it there. Then delete the temporary directory: like the post, the image leaves nothing behind but that copy.
5. Deliver it to the user as a downloadable attachment (`display: "attach"`) — never render it inline, since it's meant to be saved and uploaded elsewhere, not looked at in the chat panel.

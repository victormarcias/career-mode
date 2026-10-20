# write-daily-post

Writes the user's daily social-media reflection post, grounded in a random note from the notes folder named in `profile/profile.md`.

- **Output:** one paragraph in English, a senior engineer's take (optimistic, light wit), plus 5 to 10 hashtags, shown in chat and saved as `profile/daily-posts/daily-post-YYYYMMDD.txt` (git ignores `profile/`).
- **Topic and log:** the first line of each saved post is its topic, the note and the specific point (`Topic: dom-events/preventDefault`). `profile/daily-posts/log.csv` only says whether each post went well: `date,status` (the date as in the file name, `ok` or `error`). The skill reads both before choosing a topic so it doesn't repeat one while unused notes remain; an `error` post (the image failed or came out wrong, so it was never published) does not count as used, and its topic is reused first.
- **Doesn't:** post anywhere.
- **Optional image:** when asked, checks the Gemini key is set, runs the repo's `scripts/generate_daily_image.py` (Gemini API, key in this repo's `.env`) with its working files in a temporary folder outside the repo, saves the PNG next to the post's `.txt` with the same name, attaches it and shows the post's text again in the same reply so both can be copied, copies it to `~/Downloads` and deletes the temporary folder. A run that fails, or an image the user says came out wrong, is discarded without a retry, its image is deleted and its log line is marked `error`: the user tries again another day.

Instructions: [SKILL.md](SKILL.md).

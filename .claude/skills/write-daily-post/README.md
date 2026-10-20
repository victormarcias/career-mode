# write-daily-post

Writes the user's daily social-media reflection post, grounded in a random note from the notes folder named in `profile/profile.md`.

- **Output:** one paragraph in English, a senior engineer's take (optimistic, light wit), plus 5 to 10 hashtags, shown in chat and saved as `profile/daily-posts/daily-post-YYYYMMDD.txt` (git ignores `profile/`); if the base name is taken, use `daily-post-YYYYMMDD-2.txt`, then `-3` and subsequent numeric suffixes.
- **Topic and log:** the first line of each saved post is its topic, the note and the specific point (`Topic: dom-events/preventDefault`). `profile/daily-posts/log.csv` only says whether each post went well: `date,status` (the date as in the file name, `ok` or `error`). The skill reads both before choosing a topic so it doesn't repeat one while unused notes remain; an `error` post (the image failed or came out wrong, so it was never published) does not count as used, and its topic is reused first.
- **Doesn't:** post anywhere.
- **Optional image:** when asked, checks the Gemini key is set, runs the repo's `scripts/generate_daily_image.py` (Gemini API, key in this repo's `.env`) with its working files in a temporary folder outside the repo, saves the PNG next to the post's `.txt` with the same base name (adding `-2`, `-3`, etc. if the image filename is taken), attaches it and shows the post's text again in the same reply so both can be copied, copies it to `~/Downloads` and deletes the temporary folder. If generation fails or the user rejects the image, discard only that image-generation run without retrying, delete its image and temporary files, and retain the post’s `.txt`. Before changing the log row, determine whether the text was published (ask if unknown): mark it `error` only if unpublished; preserve a published post’s status. The user tries again another day.

Instructions: [SKILL.md](SKILL.md).

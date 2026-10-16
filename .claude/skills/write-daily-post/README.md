# write-daily-post

Writes the user's daily social-media reflection post, grounded in a random note from the notes folder named in `profile/profile.md`.

- **Output:** one paragraph in English, a senior engineer's take (optimistic, light wit), plus 5 to 10 hashtags, shown in chat only.
- **Doesn't:** post anywhere, save a draft or keep a log of past topics. That is deliberate.
- **Optional image:** when asked, checks the Gemini key is set, runs the repo's `scripts/generate_daily_image.py` (Gemini API, key in this repo's `.env`) with its working files in a temporary folder outside the repo, attaches the PNG, copies it to `~/Downloads` and deletes the temporary folder.

Instructions: [SKILL.md](SKILL.md).

# write-daily-post

Writes the user's daily social-media reflection post, grounded in a random note
from the notes folder named in `profile/profile.md`: one paragraph in English
with 5 to 10 hashtags, shown in chat and saved as
`profile/daily-posts/daily-post-YYYYMMDD.txt`. Its first line is the topic, and
`log.csv` records whether each post went well, so a topic is not repeated while
unused notes remain and a failed post's topic is reused first.

When asked, it also generates an image with the repo's
`scripts/generate_daily_image.py` (Gemini API, key in `.env`), saves it next to
the post, shows the text again and copies it to `~/Downloads`; a failed or wrong
image is discarded without a retry. It never posts anywhere. It touches
`profile/daily-posts/` and the Gemini API. Instructions: [SKILL.md](SKILL.md).

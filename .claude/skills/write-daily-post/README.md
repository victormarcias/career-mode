# write-daily-post

Writes the user's daily social-media reflection post on the topic given as the
command's input (`/write-daily-post <topic>`; with none, it asks): one short
paragraph (about 90 words) in English with 3 to 5 hashtags, shown in chat and
saved as `profile/daily-posts/daily-post-YYYYMMDD.txt`. Its first line is the
topic, and `log.csv` records whether each post went well.

When asked, it also generates an image with the repo's
`generate_daily_image.py` (Gemini API, key in `.env`), saves it next to
the post, shows the text again and copies it to `~/Downloads`. When Gemini gives
no image, it draws one itself as an SVG rendered to PNG; an image the user calls
wrong is discarded. It never posts anywhere. It touches
`profile/daily-posts/` and the Gemini API. Instructions: [SKILL.md](SKILL.md).

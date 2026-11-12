# links-inbox

Reads the user's job group with their own Telegram account (`read_group.py`,
Telethon, read only) and picks the offers that fit (work from Argentina, Python,
JavaScript or AI roles). It queues each one's link as a pending application, and
lists the offers that give no link. It sends and answers nothing in Telegram.

The credentials (`TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_PHONE_NUMBER` for the login) go in `.env`, and the
session in `private/data/telegram.session`; both stay out of git. The time of the last
message read is kept in `private/data/links-inbox-last.txt`. Telegram Web with Claude in
Chrome is the fallback, and `inbox.py` the alternative for a bot. `private/` is
gitignored. It runs every day as the first step of `/wake-up`; on a new machine, sign in with
`read_group.py --login` in a terminal (it only asks for the code Telegram sends,
the phone comes from `.env`; do it again whenever Telegram logs the session out). The script never prompts: if there is no
session it exits and says so. Instructions: [SKILL.md](SKILL.md).

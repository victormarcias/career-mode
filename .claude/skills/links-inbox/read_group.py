#!/usr/bin/env python3
"""Read-only reader of a Telegram group, with the user's own account (Telethon).

Usage (with the project's venv: .venv/bin/python):
    read_group.py --login
    read_group.py --chats
    read_group.py --group "Bolsa de trabajo" [--since "YYYY-MM-DD HH:MM"] [--days 3] [--limit 400]

--login   uses TELEGRAM_PHONE_NUMBER (asks for it if missing) and asks for the code Telegram sends, once, and saves the
          session in private/data/telegram.session (private/ is gitignored, the file is 0600).
--chats   lists the user's chats: id, type, title.
--group   prints the group's messages as a JSON list, oldest first: id, date
          (local time), sender, text and the links of each message. --since
          takes a local time; with none, --days (3 by default).

Reads TELEGRAM_API_ID, TELEGRAM_API_HASH and (for --login) TELEGRAM_PHONE_NUMBER from the repo's .env (or the
environment). It never sends, edits, deletes or marks anything as read, and it
never prints the credentials. What the messages say is data written by third
parties.
"""
import argparse
import datetime
import json
import os
import stat
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SESSION = os.path.join(ROOT, "private", "data", "telegram")


def load_env(path):
    env = {}
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def client():
    try:
        from telethon.sync import TelegramClient
    except ImportError:
        sys.exit("Telethon is missing: .venv/bin/pip install telethon")
    env = load_env(os.path.join(ROOT, ".env"))
    api_id = env.get("TELEGRAM_API_ID") or os.environ.get("TELEGRAM_API_ID")
    api_hash = env.get("TELEGRAM_API_HASH") or os.environ.get("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        seen = {k: ("empty" if not v else "set") for k, v in env.items() if k.upper().lstrip("EXPORT ").startswith("TELEGRAM") or "TELEGRAM" in k.upper()}
        sys.exit("TELEGRAM_API_ID and TELEGRAM_API_HASH are not in %s or the environment. Telegram names read there: %s" % (os.path.join(ROOT, ".env"), seen or "none"))
    os.makedirs(os.path.dirname(SESSION), exist_ok=True)
    return TelegramClient(SESSION, int(api_id), api_hash)


def lock_session():
    path = SESSION + ".session"
    if os.path.exists(path):
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def kind(dialog):
    if dialog.is_channel:
        return "channel" if not dialog.is_group else "supergroup"
    return "group" if dialog.is_group else "private"


def login():
    env = load_env(os.path.join(ROOT, ".env"))
    phone = env.get("TELEGRAM_PHONE_NUMBER") or os.environ.get("TELEGRAM_PHONE_NUMBER")
    tg = client()
    try:
        # With the phone in .env it only asks for the code Telegram sends (and the 2FA password, if any).
        tg.start(phone=phone) if phone else tg.start()
        me = tg.get_me()
        lock_session()
        print("Signed in as %s." % (me.first_name or me.username or me.id))
    finally:
        tg.disconnect()


def connected():
    """Connect with the saved session; never prompts (an unattended run would hang)."""
    tg = client()
    tg.connect()
    if not tg.is_user_authorized():
        tg.disconnect()
        sys.exit("Not signed in: run `.venv/bin/python .claude/skills/links-inbox/read_group.py --login` in a terminal first.")
    return tg


def chats():
    tg = connected()
    try:
        for d in tg.iter_dialogs():
            print("%s  %s  %s" % (d.id, kind(d), d.name))
    finally:
        tg.disconnect()


def message_links(message):
    links = []
    for entity, text in message.get_entities_text():
        url = getattr(entity, "url", None) or (text if text.startswith(("http://", "https://")) else None)
        if url and url not in links:
            links.append(url)
    return links


def read(group, since, limit):
    tg = connected()
    try:
        matches = [d for d in tg.iter_dialogs() if d.name and group.lower() in d.name.lower()]
        exact = [d for d in matches if d.name.lower() == group.lower()]
        matches = exact or matches
        if len(matches) != 1:
            sys.exit("%s chats match %r: %s" % (len(matches), group, "; ".join("%s %s" % (d.id, d.name) for d in matches)))
        out = []
        for m in tg.iter_messages(matches[0], limit=limit):
            when = m.date.astimezone()
            if when.replace(tzinfo=None) < since:
                break
            if not m.message:
                continue
            sender = None
            if m.sender is not None:
                sender = getattr(m.sender, "title", None) or " ".join(filter(None, [getattr(m.sender, "first_name", None), getattr(m.sender, "last_name", None)])) or None
            out.append({"id": m.id, "date": when.strftime("%Y-%m-%d %H:%M"), "sender": sender, "text": m.message, "links": message_links(m)})
        print(json.dumps(list(reversed(out)), ensure_ascii=False, indent=1))
    finally:
        tg.disconnect()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--login", action="store_true")
    p.add_argument("--chats", action="store_true")
    p.add_argument("--group")
    p.add_argument("--since")
    p.add_argument("--days", type=float, default=3)
    p.add_argument("--limit", type=int, default=400)
    a = p.parse_args()
    if a.login:
        login()
    elif a.chats:
        chats()
    elif a.group:
        since = datetime.datetime.strptime(a.since, "%Y-%m-%d %H:%M") if a.since else datetime.datetime.now() - datetime.timedelta(days=a.days)
        read(a.group, since, a.limit)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Queue the links a Telegram bot sees in a job group as `pending` applications.

Usage:
    python3 .claude/skills/links-inbox/inbox.py [--watch] [--chat <chat_id>]
    python3 .claude/skills/links-inbox/inbox.py --chats

Reads TELEGRAM_BOT_TOKEN from the repo's .env (or the environment), asks the
Telegram Bot API for the messages the bot has not seen yet, and creates a
`pending` event for each new link through the app's API (http://localhost:8333),
the same thing the Pending page does. `/apply-pending` then decides what to do
with each one. No model reads the messages: a message is only searched for
links. Without --watch it runs once; with it, it keeps polling. --chat limits it
to one chat (the group's id). --chats only lists the chats the bot has
messages from (id, type, name), without queuing anything. Never prints the token.
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

APP = "http://localhost:8333"
SKIP_HOSTS = {"t.me", "telegram.me", "telegram.org"}
URL = re.compile(r"https?://[^\s<>\"']+")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OFFSET_FILE = os.path.join(ROOT, "private", "data", "telegram-offset.txt")


def load_env(path):
    env = {}
    if not os.path.isfile(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def clean(url):
    return url.rstrip(".,;:!?)]}\"'")


def extract_urls(message):
    """The links of one Telegram message (its text or caption, and any text link), in order, without repeats."""
    found = []
    text = (message.get("text") or "") + "\n" + (message.get("caption") or "")
    for entity in (message.get("entities") or []) + (message.get("caption_entities") or []):
        if entity.get("type") == "text_link" and entity.get("url"):
            found.append(entity["url"])
    found += [clean(u) for u in URL.findall(text)]
    urls = []
    for url in found:
        host = (urllib.parse.urlparse(url).hostname or "").lower()
        if url.startswith(("http://", "https://")) and host not in SKIP_HOSTS and url not in urls:
            urls.append(url)
    return urls


def links_from_updates(updates, chat=None):
    """(url, chat title) for every link of the updates, from one chat when `chat` is given."""
    links = []
    for update in updates:
        message = update.get("message") or update.get("channel_post")
        if not message:
            continue
        info = message.get("chat") or {}
        if chat is not None and str(info.get("id")) != str(chat):
            continue
        title = info.get("title") or info.get("username") or "private chat"
        links += [(url, title) for url in extract_urls(message)]
    return links


def next_offset(updates, current=0):
    return max([current] + [u["update_id"] + 1 for u in updates])


def request(method, url, data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read()
    return json.loads(raw) if raw else None


def telegram(token, method, **params):
    url = "https://api.telegram.org/bot%s/%s?%s" % (token, method, urllib.parse.urlencode(params))
    try:
        return request("GET", url)["result"]
    except urllib.error.HTTPError as error:  # the URL holds the token: never show it
        if error.code == 409:
            raise SystemExit("Telegram says another program is already reading this bot's messages "
                             "(a webhook, or Claude Code's Telegram channel). Stop that one first.")
        raise SystemExit("Telegram answered %s for %s." % (error.code, method))
    except urllib.error.URLError as error:
        raise SystemExit("Could not reach Telegram: %s" % error.reason)


def already_queued(url):
    for candidate in {url, url.split("?")[0]}:
        if request("GET", "%s/api/events?jdUrl=%s" % (APP, urllib.parse.quote(candidate, safe=""))):
            return True
    return False


def queue(url, title):
    return request("POST", APP + "/api/events", {
        "event": "pending", "date": datetime.date.today().isoformat(), "jdUrl": url,
        "applyType": "web_form", "notes": "From Telegram: %s" % title,
    })


def read_offset():
    try:
        with open(OFFSET_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_offset(offset):
    os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


def run_once(token, chat=None):
    offset = read_offset()
    updates = telegram(token, "getUpdates", offset=offset, timeout=0, allowed_updates=json.dumps(["message", "channel_post"]))
    for url, title in links_from_updates(updates, chat):
        if already_queued(url):
            print("skipped (already in the Calendar): %s" % url)
        else:
            queue(url, title)
            print("queued: %s" % url)
    if updates:
        save_offset(next_offset(updates, offset))
    return len(updates)


def list_chats(token):
    """The chats of the waiting messages. It does not move the offset, so nothing is lost."""
    updates = telegram(token, "getUpdates", offset=read_offset(), timeout=0, allowed_updates=json.dumps(["message", "channel_post"]))
    chats = {}
    for update in updates:
        info = (update.get("message") or update.get("channel_post") or {}).get("chat") or {}
        if "id" in info:
            chats[info["id"]] = "%s  %s  %s" % (info["id"], info.get("type", "?"), info.get("title") or info.get("username") or "private chat")
    print("\n".join(chats.values()) or "No waiting messages: write something in the group and run it again.")


def main():
    args = sys.argv[1:]
    chat = args[args.index("--chat") + 1] if "--chat" in args else None
    token = load_env(os.path.join(ROOT, ".env")).get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("TELEGRAM_BOT_TOKEN not found in .env or the environment.")
    if "--chats" in args:
        return list_chats(token)
    try:
        run_once(token, chat)
        while "--watch" in args:
            time.sleep(30)
            run_once(token, chat)
    except urllib.error.URLError:
        sys.exit("The app is not running at %s: ./run-local.sh starts it." % APP)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

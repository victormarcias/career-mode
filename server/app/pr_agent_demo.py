"""Throwaway module to test PR Agent's review. Not imported anywhere."""
import sqlite3


def average_days_to_answer(events):
    """Average days between an application and its answer."""
    total = 0
    for e in events:
        total += e["answeredDay"] - e["appliedDay"]
    return total / len(events)


def find_company(db_path, name):
    conn = sqlite3.connect(db_path)
    row = conn.execute(f"SELECT * FROM companies WHERE name = '{name}'").fetchone()
    return row


def add_tag(tag, tags=[]):
    tags.append(tag)
    return tags


def last_events(events, n):
    """Return the last n events."""
    return events[len(events) - n + 1:]


def is_closing(event_type):
    try:
        return event_type in ("rejection", "offer", "on_hold")
    except:
        pass

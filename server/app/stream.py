"""Tells every open page that the data changed (Server-Sent Events).

A background task watches the database file, so a change made by anything
(this server, a skill, the command line) reaches the pages, not just the
changes that went through the API.
"""
import asyncio
import sqlite3
from pathlib import Path

PING_SECONDS = 15
POLL_SECONDS = 0.4


class Broadcaster:
    def __init__(self):
        self._queues: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=20)
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._queues.discard(queue)

    def publish(self):
        for queue in list(self._queues):
            try:
                queue.put_nowait('changed')
            except asyncio.QueueFull:
                pass  # that page already has a refresh pending


def _data_version(conn: sqlite3.Connection) -> int:
    return conn.execute('PRAGMA data_version').fetchone()[0]


async def watch_database(db_path: Path, broadcaster: Broadcaster):
    """`data_version` changes whenever another connection commits to the file."""
    conn = sqlite3.connect(db_path)
    try:
        last = _data_version(conn)
        while True:
            await asyncio.sleep(POLL_SECONDS)
            current = _data_version(conn)
            if current != last:
                last = current
                broadcaster.publish()
    finally:
        conn.close()


async def event_stream(broadcaster: Broadcaster):
    queue = broadcaster.subscribe()
    try:
        yield 'retry: 1000\n\n'
        while True:
            try:
                await asyncio.wait_for(queue.get(), PING_SECONDS)
                yield 'data: changed\n\n'
            except asyncio.TimeoutError:
                yield ': ping\n\n'  # keeps the connection from being cut as idle
    finally:
        broadcaster.unsubscribe(queue)

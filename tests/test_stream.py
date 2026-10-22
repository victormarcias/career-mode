"""The "something changed" channel."""
import asyncio
import sqlite3
import threading

import httpx2 as httpx
import pytest

from app.stream import Broadcaster


def test_a_published_change_reaches_every_subscriber():
    async def scenario():
        b = Broadcaster()
        first, second = b.subscribe(), b.subscribe()
        b.publish()
        assert await first.get() == 'changed' and await second.get() == 'changed'
        b.unsubscribe(second)
        b.publish()
        assert await first.get() == 'changed' and second.empty()

    asyncio.run(scenario())


def test_a_slow_page_never_blocks_the_others():
    async def scenario():
        b = Broadcaster()
        slow = b.subscribe()
        for _ in range(100):
            b.publish()  # far more than the queue holds: the extra ones are dropped, nothing raises
        assert slow.qsize() == 20

    asyncio.run(scenario())


def _read_until(lines, needle, limit=40):
    """Reads from one shared line iterator (a stream can only be iterated once)."""
    for _, line in zip(range(limit), lines):
        if needle in line:
            return line
    return None


@pytest.mark.parametrize('how', ['api', 'another process'])
def test_a_change_is_announced_whoever_makes_it(live_server, how):
    port, db_path = live_server
    base = 'http://127.0.0.1:%d' % port

    def change():
        if how == 'api':
            httpx.post(base + '/api/companies', json={'name': 'Acme', 'companyType': 'agency'})
        else:  # what a skill or the CLI does: write to the file directly
            conn = sqlite3.connect(db_path)
            with conn:
                conn.execute("INSERT INTO companies (id, name, company_type) VALUES ('direct', 'Direct', 'client')")
            conn.close()

    with httpx.stream('GET', base + '/api/stream', timeout=10) as response:
        assert response.headers['content-type'].startswith('text/event-stream')
        lines = response.iter_lines()
        assert _read_until(lines, 'retry:')
        threading.Timer(0.3, change).start()
        assert _read_until(lines, 'data: changed') == 'data: changed'

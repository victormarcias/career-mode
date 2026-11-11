"""The public demo, for a host such as Cloud Run: career-mode with the invented data, under a path prefix and read-only.

    uvicorn serve:app --app-dir demo --host 0.0.0.0 --port 8080      (what the Dockerfile runs)

- The prefix (DEMO_PREFIX, /demo/career-mode by default) is what the portfolio's rewrite sends here. It is removed before
  the app sees the request, so the app itself is the one that runs on your computer, unchanged.
- Read-only: anything but GET, HEAD and OPTIONS is refused, so a visitor can look but not change or delete.
- The data is made when the process starts, in a temporary folder, dated around that day. The process exits when the
  date changes, and the host starts a fresh one on the next visit, so "this week" never gets old.
- No .env: Settings shows nothing set and nothing can be sent. The Host header is replaced, because a public host
  is not localhost and the app only answers to localhost.
"""
import datetime as dt
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'server'))
sys.path.insert(0, str(HERE))

import cli  # noqa: E402
import make_demo  # noqa: E402
from app.main import create_app  # noqa: E402

PREFIX = os.environ.get('DEMO_PREFIX', '/demo/career-mode').rstrip('/')
WORK = Path(tempfile.mkdtemp(prefix='career-mode-demo-'))
READ_ONLY = {'GET', 'HEAD', 'OPTIONS'}


def prepare():
    sys.argv = ['make_demo.py', str(WORK)]
    make_demo.main()
    cli.main(['import', str(WORK), '--db', str(WORK / 'demo.db')])


def exit_at_midnight():
    started = dt.date.today()
    while dt.date.today() == started:
        time.sleep(60)
    os._exit(0)


class Prefixed:
    """Serves `inner` under PREFIX, read-only."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            return await self.inner(scope, receive, send)
        path = scope.get('path', '')
        if scope['type'] != 'http':
            return await self.respond(send, 404, b'Not found')
        if path == PREFIX:
            return await self.respond(send, 308, b'', [(b'location', (PREFIX + '/').encode())])
        if not path.startswith(PREFIX + '/'):
            return await self.respond(send, 404, b'Not found')
        if scope['method'] not in READ_ONLY:
            return await self.respond(send, 403, b'{"detail": "This is a read-only demo."}', [(b'content-type', b'application/json')])
        stripped = path[len(PREFIX):]
        headers = [(k, v) for k, v in scope['headers'] if k != b'host'] + [(b'host', b'localhost')]
        scope = dict(scope, path=stripped, raw_path=stripped.encode(), root_path=PREFIX, headers=headers)
        return await self.inner(scope, receive, send)

    @staticmethod
    async def respond(send, status, body, headers=()):
        await send({'type': 'http.response.start', 'status': status, 'headers': list(headers)})
        await send({'type': 'http.response.body', 'body': body})


prepare()
threading.Thread(target=exit_at_midnight, daemon=True).start()
app = Prefixed(create_app(WORK / 'demo.db', env_path=WORK / 'demo.env', profile_dir=HERE / 'profile'))

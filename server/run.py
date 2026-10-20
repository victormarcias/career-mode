#!/usr/bin/env python3
"""Starts career-mode:  python server/run.py [--port 8333] [--db data/career-mode.db]"""
import argparse
import os
import socket
import sys

import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database import DEFAULT_DB_PATH  # noqa: E402
from app.main import create_app  # noqa: E402
from app.settings import DEFAULT_PORT, load_env_file  # noqa: E402


def bind(host, port):
    sock = socket.socket(socket.AF_INET6 if ':' in host else socket.AF_INET)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    return sock


def main():
    load_env_file()  # PORT can live in .env
    parser = argparse.ArgumentParser(description='career-mode: the app and its API, on localhost.')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', DEFAULT_PORT)))
    parser.add_argument('--db', default=str(DEFAULT_DB_PATH), help='SQLite file (created if missing)')
    args = parser.parse_args()

    sockets = []
    try:
        sockets.append(bind('127.0.0.1', args.port))
    except OSError as err:
        sys.exit('Could not listen on port %d (%s). Is it already running? Try --port.' % (args.port, err))
    try:
        # macOS resolves "localhost" to ::1 first, and a v4-only server gets refused
        # outright instead of falling back, so listen on both loopbacks.
        sockets.append(bind('::1', args.port))
    except OSError as err:
        print('IPv6 listener on ::1:%d unavailable (%s): serving IPv4 only' % (args.port, err), file=sys.stderr)

    print('career-mode on http://localhost:%d  (database: %s, API docs: /docs)' % (args.port, os.path.abspath(args.db)), flush=True)
    uvicorn.Server(uvicorn.Config(create_app(args.db), log_level='warning')).run(sockets=sockets)


if __name__ == '__main__':
    main()

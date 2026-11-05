"""career-mode: the web app plus its JSON API, on localhost.

Only the app's own files are served: everything in public/ and, from profile/, the user's outreach.md and
profile.md (or their examples) for the pages that show them, and their photo, never the database, backups or .env. Requests whose Host is
not localhost are refused (DNS rebinding), and so are writes that come from
another website (Origin check). There is no login: whoever can open
localhost:8333 is you. The API is documented at /docs.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from starlette.datastructures import Headers, MutableHeaders

from . import crud, google_calendar, mailer, profile_photo, snapshot
from .database import DEFAULT_DB_PATH, ROOT, make_engine, migrate, session_factory
from .settings import ENV_PATH
from .routes import calendar, companies, events, mail, settings as settings_routes
from .schemas import Snapshot
from .stream import Broadcaster, event_stream, watch_database

LOCAL_HOSTS = ('localhost', '127.0.0.1', '::1')
PROFILE_DIR = ROOT / 'profile'  # the user's own files in it are gitignored; the *.example.* ones ship with the repo


def _hostname(host_header: str) -> str:
    """'[::1]:8333' -> '::1', 'localhost:8333' -> 'localhost'."""
    if host_header.startswith('[') and ']' in host_header:
        return host_header[1:host_header.index(']')]
    return host_header.split(':')[0]


class LocalOnly:
    """Pure ASGI middleware: host and origin checks, and nothing is ever cached."""

    def __init__(self, app, allowed_hosts):
        self.app = app
        self.allowed_hosts = tuple(allowed_hosts)

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        host_header = headers.get('host', '')
        refusal = None
        if _hostname(host_header) not in self.allowed_hosts:
            refusal = 'Only localhost may use this server'
        elif scope['method'] not in ('GET', 'HEAD', 'OPTIONS') and headers.get('origin') not in (None, 'http://%s' % host_header):
            refusal = 'Cross-site request refused'
        if refusal:
            return await JSONResponse({'detail': refusal}, status_code=403)(scope, receive, send)

        async def send_no_store(message):
            if message['type'] == 'http.response.start':
                MutableHeaders(scope=message).setdefault('Cache-Control', 'no-store')
            await send(message)

        await self.app(scope, receive, send_no_store)


def create_app(db_path=None, allowed_hosts=LOCAL_HOSTS, env_path=None, profile_dir=None) -> FastAPI:
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        migrate(db_path)  # `alembic upgrade head`: nobody has to remember to run it
        engine = make_engine(db_path)
        app.state.engine = engine
        app.state.session_factory = session_factory(engine)
        app.state.broadcaster = Broadcaster()
        app.state.env_path = Path(env_path) if env_path else ENV_PATH
        app.state.profile_dir = Path(profile_dir) if profile_dir else PROFILE_DIR
        app.state.fetch_ics = google_calendar.fetch_ics  # replaced in tests, so none of them reaches Google
        app.state.send_mail = mailer.smtp_send  # replaced in tests, so none of them sends an email
        watcher = asyncio.create_task(watch_database(db_path, app.state.broadcaster))
        yield
        watcher.cancel()
        engine.dispose()

    app = FastAPI(
        title='career-mode',
        version='1.0',
        description='The job-search tracker: companies (agencies and clients) and the events of each process. Everything is on this computer, in one SQLite file.',
        lifespan=lifespan,
    )
    app.add_middleware(LocalOnly, allowed_hosts=allowed_hosts)

    @app.exception_handler(crud.DomainError)
    async def domain_error(_request: Request, err: crud.DomainError):
        return JSONResponse({'detail': err.message}, status_code=err.status)

    @app.exception_handler(IntegrityError)
    async def integrity_error(_request: Request, err: IntegrityError):  # a database rule the checks above missed
        return JSONResponse({'detail': 'The database refused it: %s' % str(err.orig)}, status_code=409)

    app.include_router(companies.router)
    app.include_router(events.router)
    app.include_router(calendar.router)
    app.include_router(mail.router)
    app.include_router(settings_routes.router)

    @app.get('/api/export', response_model=Snapshot, tags=['backup'], summary='Everything, as JSON')
    def export(request: Request):
        with request.app.state.session_factory() as session:
            return snapshot.export_snapshot(session)

    @app.get('/api/stream', tags=['backup'], summary='Server-Sent Events: "changed" whenever the data does',
             response_class=StreamingResponse)
    async def stream(request: Request):
        return StreamingResponse(event_stream(request.app.state.broadcaster), media_type='text/event-stream')

    # ----- the app's own files, and only those -----

    # The Outreach page's messages and the My Profile page's profile are the user's own, so they come from
    # profile/outreach.md and profile/profile.md (gitignored) and, until those exist, from the example next to each.
    # Only these two files are served from profile/, and only to the pages of this app on localhost. A header says
    # when what is served is still the example (or an untouched copy of it), so the page can offer to make it the
    # user's own.
    def own_or_example(request: Request, stem: str):
        folder = request.app.state.profile_dir
        example = folder / ('%s.example.md' % stem)
        for name in ('%s.md' % stem, '%s.example.md' % stem):
            path = folder / name
            if path.is_file():
                is_example = name.endswith('.example.md') or (example.is_file() and path.read_bytes() == example.read_bytes())
                return FileResponse(path, media_type='text/markdown; charset=utf-8', headers={'X-Profile-Example': 'true' if is_example else 'false'})
        return JSONResponse({'detail': 'Not found'}, status_code=404)

    @app.get('/outreach.md', include_in_schema=False)
    def outreach_messages(request: Request):
        return own_or_example(request, 'outreach')

    @app.get('/profile.md', include_in_schema=False)
    def my_profile(request: Request):
        return own_or_example(request, 'profile')

    # The photo kept in profile/ (uploaded in Settings), for the page that shows it. Only this file.
    @app.get('/profile-files/photo', include_in_schema=False)
    def serve_profile_photo(request: Request):
        path = profile_photo.photo_path(request.app.state.profile_dir)
        if path is None:
            return JSONResponse({'detail': 'Not found'}, status_code=404)
        return FileResponse(path, media_type=profile_photo.media_type(path), headers={'X-Content-Type-Options': 'nosniff'})

    # The whole front end lives in public/ and is served from the root (/, /style.css, /js/main.js,
    # /navigation/...). Mounted last, so it only gets what no route above wanted.
    app.mount('/', StaticFiles(directory=ROOT / 'public', html=True), name='public')
    return app

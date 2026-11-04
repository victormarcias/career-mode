"""The local settings the app keeps in the project's .env file.

Only the variables listed in ENV_VARS can be read or written through the API, so
adding a setting is adding one entry here. A secret is never sent back in the list: the
API only says whether it is set and how long it is, and its full value
comes from its own route, when the eye icon asks for it. A value
exported in the shell wins over this file when the server starts.
"""
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import google_calendar
from .database import ROOT

ENV_PATH = ROOT / '.env'
MAX_CV_BYTES = 1 * 1024 * 1024
DEFAULT_PORT = '8333'
BACKUP_DIR = 'backup'  # always this folder, inside the project: git ignores it. Like PORT, it is not a setting the page lists


@dataclass(frozen=True)
class EnvVar:
    # In `description`, text between backticks is a filename or a command: the page shows it as code.
    name: str
    label: str
    description: str
    secret: bool = False
    default: Optional[str] = None
    restart_required: bool = False  # read once when the server starts
    choices: Optional[tuple] = None  # the only values it accepts, which the page offers as a list


ENV_VARS = [  # in alphabetical order, which is how Settings lists them
    EnvVar(
        'APP_LANGUAGE',
        'Language',
        'The language of the app: `en` (English) or `es` (Spanish). It applies when the page reloads.',
        default='en',
        choices=('en', 'es'),
    ),
    EnvVar(
        'CV_PDF_PATH',
        'CV file',
        'The path to your CV as a PDF of up to 1 MB on this computer. `/setup` copies it to `profile/cv.pdf` and fills this in; '
        'run it again when your CV changes. A relative path starts at the project folder. The skills attach and upload '
        'this file, and `/read-cv` reads it.',
    ),
    EnvVar(
        'EMAIL_ADDRESS',
        'Email address',
        'The address the application emails are sent from (the skills send through it, with no browser). It works with '
        'any provider that has an SMTP server: Gmail by default, or set `EMAIL_SMTP_HOST` for another one.',
    ),
    EnvVar(
        'EMAIL_PASSWORD',
        'Email password',
        'The password to send with. Gmail needs an app password, not the account one (Google account, Security, '
        '2-Step Verification, App passwords; spaces are ignored); other providers say which they want.',
        secret=True,
    ),
    EnvVar(
        'EMAIL_SMTP_HOST',
        'SMTP server',
        'The provider\'s outgoing mail server. Gmail\'s is the default.',
        default='smtp.gmail.com',
    ),
    EnvVar(
        'EMAIL_SMTP_PORT',
        'SMTP port',
        'The server\'s port: 465 (secure from the start) or 587 (STARTTLS).',
        default='465',
    ),
    EnvVar(
        'GEMINI_API_KEY',
        'Gemini API key',
        'Used to generate the image of a thought reflection.',
        secret=True,
    ),
    EnvVar(
        'GOOGLE_CALENDAR_ID',
        'Google Calendar ID',
        'What the Google Calendar button of the Calendar reads. Either the ID of your calendar (Google Calendar, Settings, your calendar, '
        'Integrate calendar), which has to be public with "See all event details", or its secret address in iCal format, '
        'which also works for a private one.',
        secret=True,
    ),
    EnvVar(
        'GOOGLE_TASKS_CLIENT_ID',
        'Google Tasks client ID',
        'What the Google Tasks button reads: it queues the links of your open tasks and marks those tasks as done. In the Google Cloud Console enable the Google Tasks API, '
        'set up the OAuth consent screen (add yourself as a test user) and create an OAuth client ID of type Web application, with '
        '`https://developers.google.com/oauthplayground` as an authorized redirect URI. This is its client ID.',
        secret=True,
    ),
    EnvVar(
        'GOOGLE_TASKS_CLIENT_SECRET',
        'Google Tasks client secret',
        'The secret of that OAuth client.',
        secret=True,
    ),
    EnvVar(
        'GOOGLE_TASKS_REFRESH_TOKEN',
        'Google Tasks refresh token',
        'In the OAuth Playground (`https://developers.google.com/oauthplayground`), open its settings, tick "Use your own OAuth '
        'credentials" and paste the client ID and secret above. Write the scope `https://www.googleapis.com/auth/tasks`, '
        'authorize, press "Exchange authorization code for tokens" and paste the refresh token here. While the consent screen is '
        'in Testing, Google expires it after 7 days: publish the app to keep it.',
        secret=True,
    ),
]
# What a variable used to be called: an install that still has the old name keeps working, and saving the new name removes it.
LEGACY_NAMES = {'GOOGLE_CALENDAR_ID': 'CALENDAR_ID'}
BY_NAME = {v.name: v for v in ENV_VARS}

_LINE = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$')
_PLAIN = re.compile(r'[A-Za-z0-9_./:@+,-]*')


def _unquote(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return re.sub(r'\\(["\\])', r'\1', raw[1:-1])
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1]
    return re.split(r'\s+#', raw, maxsplit=1)[0].strip()  # an unquoted value ends at " # comment"


def _quote(value: str) -> str:
    return value if _PLAIN.fullmatch(value) else '"%s"' % value.replace('\\', '\\\\').replace('"', '\\"')


def read_env_file(path: Path = ENV_PATH) -> dict:
    try:
        lines = Path(path).read_text(encoding='utf-8').splitlines()
    except FileNotFoundError:
        return {}
    values = {}
    for line in lines:
        match = _LINE.match(line)
        if match and not line.lstrip().startswith('#'):
            values[match.group(1)] = _unquote(match.group(2))
    return values


def load_env_file(path: Path = ENV_PATH):
    """Puts the file's values in the environment, without overriding what is already exported."""
    for name, value in read_env_file(path).items():
        os.environ.setdefault(name, value)


def validate(name: str, value: str) -> str:
    """Returns the cleaned value, or raises ValueError with a sentence to show."""
    if name not in BY_NAME:
        raise ValueError('Unknown setting "%s"' % name)
    value = value.strip()
    if not value:
        raise ValueError('"%s" is empty: remove it instead' % name)
    if '\n' in value or '\r' in value or '\x00' in value:
        raise ValueError('"%s" must be a single line' % name)
    if BY_NAME[name].choices and value not in BY_NAME[name].choices:
        raise ValueError('Choose one of: %s' % ', '.join(BY_NAME[name].choices))
    if name == 'PORT' and not (value.isdigit() and 1 <= int(value) <= 65535):
        raise ValueError('The port must be a number between 1 and 65535')
    if name == 'GEMINI_API_KEY' and re.search(r'\s', value):
        raise ValueError('An API key has no spaces')
    if name == 'EMAIL_ADDRESS' and not re.fullmatch(r'[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+', value):
        raise ValueError('That is not an email address')
    if name == 'EMAIL_SMTP_HOST' and not re.fullmatch(r'[A-Za-z0-9.-]+\.[A-Za-z]{2,}', value):
        raise ValueError('That is not a server name (for example smtp.gmail.com)')
    if name == 'EMAIL_SMTP_PORT' and value not in ('465', '587'):
        raise ValueError('The port is 465 or 587')
    if name == 'GOOGLE_CALENDAR_ID':
        google_calendar.ics_url(value)  # raises the ValueError to show
    if name == 'CV_PDF_PATH':
        path = Path(os.path.expanduser(value))
        path = path if path.is_absolute() else ROOT / path
        if not path.is_file():
            raise ValueError('There is no file at that path (a relative one starts at the project folder)')
        with open(path, 'rb') as f:
            if f.read(5) != b'%PDF-':
                raise ValueError('That file is not a PDF')
        if path.stat().st_size > MAX_CV_BYTES:
            raise ValueError('The CV is too big (%d MB at most)' % (MAX_CV_BYTES // (1024 * 1024)))
    return value


def update_env_file(updates: dict, path: Path = ENV_PATH):
    """Sets (str) or removes (None) the given variables, leaving every other line as it was."""
    path = Path(path)
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except FileNotFoundError:
        lines = []
    out, seen = [], set()
    for line in lines:
        match = _LINE.match(line)
        name = match.group(1) if match and not line.lstrip().startswith('#') else None
        if name in updates:
            seen.add(name)
            if updates[name] is not None:
                out.append('%s=%s' % (name, _quote(updates[name])))
        else:
            out.append(line)
    out += ['%s=%s' % (name, _quote(value)) for name, value in updates.items() if value is not None and name not in seen]
    temp = path.with_name(path.name + '.tmp')
    temp.write_text('\n'.join(out) + '\n' if out else '', encoding='utf-8')
    os.chmod(temp, 0o600)  # it holds secrets
    os.replace(temp, path)


def get(name: str, path: Path = ENV_PATH) -> Optional[str]:
    """What the file holds for `name`, or for the name it used to have."""
    stored = read_env_file(path)
    return stored.get(name) or stored.get(LEGACY_NAMES.get(name, '')) or None


def reveal(name: str, path: Path = ENV_PATH) -> Optional[str]:
    """The full value of a secret, for the eye icon. Raises KeyError unless `name` is a known secret."""
    var = BY_NAME.get(name)
    if var is None or not var.secret:
        raise KeyError(name)
    return get(name, path)


def describe(path: Path = ENV_PATH) -> list:
    """Every known variable with what the file holds, as the API reports it."""
    rows = []
    for var in ENV_VARS:
        value = get(var.name, path)
        rows.append({
            'name': var.name,
            'label': var.label,
            'description': var.description,
            'secret': var.secret,
            'restart_required': var.restart_required,
            'default': var.default,
            'choices': list(var.choices) if var.choices else None,
            'is_set': bool(value),
            'value': None if var.secret else (value or None),
            'length': len(value) if var.secret and value else None,
        })
    return rows

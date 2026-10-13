"""Sends an application email from the user's own address, with the CV attached.

It talks to the provider's SMTP server with the address and password of Settings (EMAIL_ADDRESS, EMAIL_PASSWORD, and
EMAIL_SMTP_HOST / EMAIL_SMTP_PORT, which default to Gmail's): any provider with an SMTP server works. Gmail has no
API key for sending, so it needs an app password; this needs no sign-in screen, no browser and no extra packages.
Nothing is kept here: Gmail itself leaves a copy in the account's Sent folder, other providers may not.
"""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Optional

import certifi

from . import settings
from .crud import DomainError
from .database import ROOT

DEFAULT_HOST = 'smtp.gmail.com'
DEFAULT_PORT = '465'


def cv_file(env_path: Path) -> Path:
    """The CV of the CV_PDF_PATH setting, which has to be set and be there."""
    value = settings.get('CV_PDF_PATH', env_path)
    if not value:
        raise DomainError(409, 'There is no CV to attach: set the CV file in Settings first (or run /setup)')
    path = Path(value).expanduser()
    path = path if path.is_absolute() else ROOT / path
    if not path.is_file():
        raise DomainError(409, 'The CV file in Settings is not there any more: %s' % value)
    return path


def build_message(sender: str, to: str, subject: str, body: str, from_name: Optional[str] = None, cv: Optional[Path] = None) -> EmailMessage:
    message = EmailMessage()
    message['From'] = formataddr((from_name, sender)) if from_name else sender
    message['To'] = to
    message['Subject'] = subject
    message.set_content(body)
    if cv is not None:
        message.add_attachment(cv.read_bytes(), maintype='application', subtype='pdf', filename=cv.name)
    return message


def smtp_send(sender: str, password: str, message: EmailMessage, host: str = DEFAULT_HOST, port: int = int(DEFAULT_PORT)) -> None:
    # certifi's certificates, not the system's (see google_calendar.fetch_ics)
    context = ssl.create_default_context(cafile=certifi.where())
    if host == DEFAULT_HOST:
        password = ''.join(password.split())  # Google shows an app password in groups of four
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
        with server:
            if port != 465:
                server.starttls(context=context)
            server.login(sender, password)
            server.send_message(message)
    except smtplib.SMTPAuthenticationError:
        raise DomainError(502, (
            'The mail server refused the address or the password. Check EMAIL_ADDRESS and EMAIL_PASSWORD in Settings '
            '(Gmail needs an app password: Google account, Security, 2-Step Verification, App passwords).'
        ))
    except smtplib.SMTPServerDisconnected:
        raise DomainError(502, (
            'The mail server closed the connection while signing in. For Gmail this usually means EMAIL_PASSWORD is not an '
            'app password (16 letters, made in Google account, Security, 2-Step Verification, App passwords).'
        ))
    except smtplib.SMTPRecipientsRefused:
        raise DomainError(422, 'The mail server refused the recipient address')
    except (smtplib.SMTPException, OSError) as err:
        raise DomainError(502, 'Could not send the email through %s: %s' % (host, err))


def send(env_path: Path, to: str, subject: str, body: str, attach_cv: bool = True, from_name: Optional[str] = None, send_with=smtp_send) -> dict:
    sender = settings.get('EMAIL_ADDRESS', env_path)
    password = settings.get('EMAIL_PASSWORD', env_path)
    if not sender or not password:
        raise DomainError(409, 'Email is not set up: set EMAIL_ADDRESS and EMAIL_PASSWORD in Settings first (or run /setup)')
    host = settings.get('EMAIL_SMTP_HOST', env_path) or DEFAULT_HOST
    port = int(settings.get('EMAIL_SMTP_PORT', env_path) or DEFAULT_PORT)
    cv = cv_file(env_path) if attach_cv else None
    send_with(sender, password, build_message(sender, to, subject, body, from_name, cv), host, port)
    return {'sent': True, 'from': sender, 'to': to, 'attached': cv.name if cv else None}

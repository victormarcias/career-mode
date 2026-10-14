"""Sending an application by email: the route, the message it builds and what it says when the mail server says no."""
import smtplib
from email import message_from_bytes, policy

import pytest

from app import mailer

CV = b'%PDF-1.4 a pretend CV'
GOOD = {'to': 'recruiter@example.org', 'subject': 'Full Stack Developer', 'body': 'Hello,\n\nHere is my CV.\n\nJane'}


@pytest.fixture
def sent(client, env_path, tmp_path):
    """Email set up (with a CV), and a recorder instead of a real mail server. `sent` is the list of what would go out."""
    cv = tmp_path / 'cv.pdf'
    cv.write_bytes(CV)
    env_path.write_text('EMAIL_ADDRESS=jane@example.org\nEMAIL_PASSWORD=app-password-1234\nCV_PDF_PATH=%s\n' % cv)
    calls = []
    client.app.state.send_mail = lambda sender, password, message, host, port: calls.append((sender, password, message, host, port))
    return calls


def test_it_sends_from_the_settings_address_with_the_cv_attached(client, sent):
    r = client.post('/api/mail/send', json=GOOD)
    assert r.status_code == 200 and r.json() == {'sent': True, 'from': 'jane@example.org', 'to': 'recruiter@example.org', 'attached': 'cv.pdf'}
    [(sender, password, message, host, port)] = sent
    assert (sender, password, host, port) == ('jane@example.org', 'app-password-1234', 'smtp.gmail.com', 465)  # Gmail unless told otherwise
    assert (message['From'], message['To'], message['Subject']) == ('jane@example.org', 'recruiter@example.org', 'Full Stack Developer')
    assert message.get_body(('plain',)).get_content() == GOOD['body'] + '\n'
    [attachment] = list(message.iter_attachments())
    assert (attachment.get_content_type(), attachment.get_filename(), attachment.get_content()) == ('application/pdf', 'cv.pdf', CV)


def test_the_password_never_comes_back(client, sent):
    assert 'app-password-1234' not in client.post('/api/mail/send', json=GOOD).text


def test_the_name_shown_next_to_the_address(client, sent):
    client.post('/api/mail/send', json={**GOOD, 'fromName': 'Jane Doe'})
    assert sent[0][2]['From'] == 'Jane Doe <jane@example.org>'


def test_without_the_cv(client, sent):
    r = client.post('/api/mail/send', json={**GOOD, 'attachCv': False})
    assert r.json()['attached'] is None and list(sent[0][2].iter_attachments()) == []


def test_another_provider_and_port_come_from_settings(client, env_path, sent):
    env_path.write_text(env_path.read_text() + 'EMAIL_SMTP_HOST=smtp.example.org\nEMAIL_SMTP_PORT=587\n')
    client.post('/api/mail/send', json=GOOD)
    assert sent[0][3:] == ('smtp.example.org', 587)


def test_the_line_breaks_of_the_body_are_kept_as_they_are(client, sent):
    body = 'one\n\ntwo\nthree\n\n\nfour'
    client.post('/api/mail/send', json={**GOOD, 'body': body})
    assert sent[0][2].get_body(('plain',)).get_content() == body + '\n'


def test_the_mail_survives_being_turned_into_bytes_and_read_back(client, sent):
    parsed = message_from_bytes(bytes(sent_message(client, sent)), policy=policy.default)
    assert parsed['Subject'] == GOOD['subject'] and len(list(parsed.iter_attachments())) == 1


def sent_message(client, sent):
    client.post('/api/mail/send', json=GOOD)
    return sent[0][2]


def test_it_refuses_when_email_is_not_set_up(client, env_path):
    r = client.post('/api/mail/send', json=GOOD)
    assert r.status_code == 409 and 'Settings' in r.json()['detail']
    env_path.write_text('EMAIL_ADDRESS=jane@example.org\n')  # an address with no password is not enough
    assert client.post('/api/mail/send', json=GOOD).status_code == 409


def test_it_refuses_to_attach_a_cv_that_is_not_set_or_not_there(client, env_path, sent, tmp_path):
    env_path.write_text('EMAIL_ADDRESS=jane@example.org\nEMAIL_PASSWORD=pw\n')
    r = client.post('/api/mail/send', json=GOOD)
    assert r.status_code == 409 and 'CV' in r.json()['detail'] and sent == []
    assert client.post('/api/mail/send', json={**GOOD, 'attachCv': False}).status_code == 200  # no CV needed without the attachment
    env_path.write_text('EMAIL_ADDRESS=jane@example.org\nEMAIL_PASSWORD=pw\nCV_PDF_PATH=%s\n' % (tmp_path / 'gone.pdf'))
    assert client.post('/api/mail/send', json=GOOD).status_code == 409


@pytest.mark.parametrize('change', [
    {'to': 'not an address'}, {'to': 'a@b.org, c@d.org'}, {'to': 'a@b.org;c@d.org'}, {'to': '<a@b.org>'}, {'to': ''},
    {'subject': ''}, {'subject': 'two\nlines'}, {'subject': 'Subject\r\nBcc: someone@example.org'},
    {'body': ''}, {'fromName': 'Jane\nBcc: someone@example.org'}, {'fromName': 'Jane <x@y.org>'},
])
def test_what_could_inject_a_header_or_a_second_recipient_is_refused(client, sent, change):
    r = client.post('/api/mail/send', json={**GOOD, **change})
    assert r.status_code == 422 and sent == []


def test_there_is_no_way_to_add_a_cc_or_bcc(client, sent):
    client.post('/api/mail/send', json={**GOOD, 'cc': 'x@y.org', 'bcc': 'z@y.org'})
    assert sent[0][2]['Cc'] is None and sent[0][2]['Bcc'] is None


def test_the_route_is_documented(client):
    assert 'post' in client.get('/openapi.json').json()['paths']['/api/mail/send']


# ---------- the real send, against a mail server that is only a recording ----------


class FakeServer:
    created = []

    def __init__(self, host, port, **kwargs):
        self.host, self.port, self.kwargs, self.calls = host, port, kwargs, []
        FakeServer.created.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append('starttls')

    def login(self, user, password):
        self.calls.append(('login', user, password))

    def send_message(self, message):
        self.calls.append(('send', message['To']))


@pytest.fixture
def smtp(monkeypatch):
    FakeServer.created = []
    monkeypatch.setattr(mailer.smtplib, 'SMTP_SSL', FakeServer)
    monkeypatch.setattr(mailer.smtplib, 'SMTP', FakeServer)
    return FakeServer


def message():
    return mailer.build_message('jane@example.org', 'recruiter@example.org', 'Hello', 'Body')


def test_port_465_is_secure_from_the_start_and_587_uses_starttls(smtp):
    mailer.smtp_send('jane@example.org', 'pw', message(), 'smtp.example.org', 465)
    mailer.smtp_send('jane@example.org', 'pw', message(), 'smtp.example.org', 587)
    ssl_first, starttls_first = smtp.created
    assert 'starttls' not in ssl_first.calls and ssl_first.calls == [('login', 'jane@example.org', 'pw'), ('send', 'recruiter@example.org')]
    assert starttls_first.calls[0] == 'starttls' and ('send', 'recruiter@example.org') in starttls_first.calls


def test_google_shows_an_app_password_in_groups_of_four_and_the_spaces_are_dropped(smtp):
    mailer.smtp_send('jane@gmail.com', 'abcd efgh ijkl mnop', message(), 'smtp.gmail.com', 465)
    assert ('login', 'jane@gmail.com', 'abcdefghijklmnop') in smtp.created[0].calls
    mailer.smtp_send('jane@example.org', 'two words', message(), 'smtp.example.org', 465)  # another provider's password is left alone
    assert ('login', 'jane@example.org', 'two words') in smtp.created[1].calls


@pytest.mark.parametrize('error, status, words', [
    (smtplib.SMTPAuthenticationError(535, b'bad'), 502, 'refused the address or the password'),
    (smtplib.SMTPServerDisconnected('closed'), 502, 'app password'),
    (smtplib.SMTPRecipientsRefused({'x': (550, b'no')}), 422, 'recipient'),
    (smtplib.SMTPException('boom'), 502, 'Could not send'),
    (OSError('no route to host'), 502, 'Could not send'),
])
def test_what_the_mail_server_says_no_to_is_a_sentence_not_a_crash(monkeypatch, error, status, words):
    class Refusing(FakeServer):
        def login(self, user, password):
            raise error

    monkeypatch.setattr(mailer.smtplib, 'SMTP_SSL', Refusing)
    with pytest.raises(mailer.DomainError) as caught:
        mailer.smtp_send('jane@example.org', 'pw', message(), 'smtp.example.org', 465)
    assert caught.value.status == status and words in caught.value.message

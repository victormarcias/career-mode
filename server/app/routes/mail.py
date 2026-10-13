from typing import Optional

from fastapi import APIRouter, Request
from pydantic import Field

from .. import mailer
from ..schemas import CamelModel

router = APIRouter(prefix='/api/mail', tags=['mail'])


class MailIn(CamelModel):
    to: str = Field(pattern=r'^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$', description='One recipient address')
    subject: str = Field(min_length=1, max_length=300, pattern=r'^[^\r\n]+$')
    body: str = Field(min_length=1, max_length=20000, description='Plain text, with its line breaks as they are')
    attach_cv: bool = Field(default=True, description='Attach the CV of the CV_PDF_PATH setting')
    from_name: Optional[str] = Field(default=None, max_length=100, pattern=r'^[^\r\n<>]*$', description='The name shown next to the sender address')


class MailOut(CamelModel):
    sent: bool
    from_: str = Field(alias='from')
    to: str
    attached: Optional[str] = Field(description='The name of the attached file, if any')


@router.post('/send', response_model=MailOut, summary='Send an email from the address in Settings',
             description=(
                 'Sends right away, from EMAIL_ADDRESS through the SMTP server of Settings, to one recipient and with no CC or BCC. '
                 'The CV (the CV_PDF_PATH setting) is attached unless attachCv is false. Gmail keeps a copy in the Sent folder.'
             ))
def send_mail(data: MailIn, request: Request):
    return mailer.send(request.app.state.env_path, data.to, data.subject, data.body, data.attach_cv, data.from_name, request.app.state.send_mail)

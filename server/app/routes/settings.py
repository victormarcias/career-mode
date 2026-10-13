from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .. import profile_photo, settings
from ..crud import DomainError
from ..schemas import CamelModel

router = APIRouter(prefix='/api/settings', tags=['settings'])


class EnvVarOut(CamelModel):
    name: str
    label: str
    description: str
    secret: bool
    restart_required: bool = Field(description='Read once when the server starts, so a change applies after a restart')
    default: Optional[str]
    choices: Optional[list[str]] = Field(default=None, description='The only values it accepts, when it is a choice')
    is_set: bool
    value: Optional[str] = Field(description='What the .env file holds; always empty for a secret')
    length: Optional[int] = Field(description='For a secret that is set: how many characters it has, so the page can draw as many dots')


class SecretValue(BaseModel):
    name: str
    value: Optional[str] = Field(description='The full value, or null when it is not set')


class EnvUpdate(BaseModel):
    values: dict[str, Optional[str]] = Field(description='Only the variables to change: a value sets it, null (or blank) removes it')


@router.get('/env', response_model=list[EnvVarOut], summary='The local environment variables the app knows about',
            description='Kept in the .env file at the project folder. A secret is never returned in full here.')
def get_env(request: Request):
    return settings.describe(request.app.state.env_path)


@router.get('/env/{name}/value', response_model=SecretValue, summary='The full value of one secret',
            description=(
                'What the eye icon shows. Only for settings marked secret (anything else is a 404): the list above never '
                'returns a secret in full.'
            ))
def get_secret(name: str, request: Request):
    try:
        value = settings.reveal(name, request.app.state.env_path)
    except KeyError:
        raise DomainError(404, 'No secret setting named "%s"' % name)
    return {'name': name, 'value': value}


@router.put('/env', response_model=list[EnvVarOut], summary='Set or remove some of them',
            description='Variables not mentioned are left alone, and so is everything else in the .env file.')
def put_env(update: EnvUpdate, request: Request):
    cleaned = {}
    for name, value in update.values.items():
        if name not in settings.BY_NAME:
            raise DomainError(422, 'Unknown setting "%s"' % name)
        if value is None or not value.strip():
            cleaned[name] = None
            continue
        try:
            cleaned[name] = settings.validate(name, value)
        except ValueError as err:
            raise DomainError(422, str(err))
    for name in list(cleaned):  # saving (or removing) a variable also drops the name it used to have
        if name in settings.LEGACY_NAMES:
            cleaned[settings.LEGACY_NAMES[name]] = None
    settings.update_env_file(cleaned, request.app.state.env_path)
    return settings.describe(request.app.state.env_path)


class PhotoOut(CamelModel):
    name: str
    size: int
    updated: str = Field(description='When the file was last written, as an ISO date and time')


@router.get('/photo', response_model=Optional[PhotoOut], summary='The profile photo kept in profile/',
            description='null when there is none.')
def get_photo(request: Request):
    return profile_photo.photo_info(request.app.state.profile_dir)


@router.put('/photo', response_model=PhotoOut, summary='Replace the profile photo',
            description=(
                'The request body is the image itself (not a form): a PNG or JPEG of up to 1 MB, judged by its content. '
                'It is saved as profile/photo.<ext>.'
            ))
async def put_photo(request: Request):
    declared = request.headers.get('content-length')
    if declared and declared.isdigit() and int(declared) > profile_photo.MAX_PHOTO_BYTES:
        raise DomainError(413, 'The photo is too big (%d MB at most)' % (profile_photo.MAX_PHOTO_BYTES // (1024 * 1024)))
    data = await request.body()
    try:
        return profile_photo.save_photo(request.app.state.profile_dir, data)
    except ValueError as err:
        raise DomainError(422, str(err))


@router.delete('/photo', status_code=204, summary='Remove the profile photo')
def delete_photo(request: Request):
    if not profile_photo.remove_photo(request.app.state.profile_dir):
        raise DomainError(404, 'There is no photo to remove')

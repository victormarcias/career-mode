"""The profile photo, the one file Settings keeps in profile/ (photo.png or photo.jpg), which git ignores.

The skills upload it to forms that ask for a profile picture. It is judged by its first bytes, never by the name or the
type the browser says, and only one is kept: a photo of another type replaces the old one.
"""
import datetime
import os
from pathlib import Path
from typing import Optional

MAX_PHOTO_BYTES = 1 * 1024 * 1024

_PHOTO_NAMES = ['photo.png', 'photo.jpg']
_MEDIA = {'.png': 'image/png', '.jpg': 'image/jpeg'}


def _extension(data: bytes) -> str:
    """The extension the content calls for, judged by its first bytes. Raises ValueError with a sentence to show."""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if data.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    raise ValueError('The photo has to be a PNG or JPEG image')


def photo_path(profile_dir: Path) -> Optional[Path]:
    for name in _PHOTO_NAMES:
        path = Path(profile_dir) / name
        if path.is_file():
            return path
    return None


def media_type(path: Path) -> str:
    return _MEDIA.get(path.suffix, 'application/octet-stream')


def photo_info(profile_dir: Path) -> Optional[dict]:
    path = photo_path(profile_dir)
    if path is None:
        return None
    stat = path.stat()
    return {
        'name': path.name,
        'size': stat.st_size,
        'updated': datetime.datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec='seconds'),
    }


def save_photo(profile_dir: Path, data: bytes) -> dict:
    """Replaces the photo. Raises ValueError with a sentence to show when it is empty, too big or not an image."""
    if not data:
        raise ValueError('The file is empty')
    if len(data) > MAX_PHOTO_BYTES:
        raise ValueError('The photo is too big (%d MB at most)' % (MAX_PHOTO_BYTES // (1024 * 1024)))
    extension = _extension(data)
    profile_dir = Path(profile_dir)
    profile_dir.mkdir(exist_ok=True)
    target = profile_dir / ('photo' + extension)
    temp = target.with_name(target.name + '.tmp')
    temp.write_bytes(data)
    os.replace(temp, target)
    for name in _PHOTO_NAMES:  # a photo of another type must not linger next to the new one
        other = profile_dir / name
        if other != target and other.is_file():
            other.unlink()
    return photo_info(profile_dir)


def remove_photo(profile_dir: Path) -> bool:
    removed = False
    for name in _PHOTO_NAMES:
        path = Path(profile_dir) / name
        if path.is_file():
            path.unlink()
            removed = True
    return removed

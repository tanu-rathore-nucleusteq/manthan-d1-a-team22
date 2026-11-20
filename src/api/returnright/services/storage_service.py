"""Saves uploaded photos to the upload folder: allowed types and size checked, files renamed."""

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from returnright.core.exceptions import PhotoRejectedError, PhotoTooLargeError
from returnright.utils.clock import Clock

# The type is decided from the file's first bytes, never from its name or the browser's header.
SIGNATURES = {
    b"\xff\xd8\xff": ("jpg", "image/jpeg"),
    b"\x89PNG\r\n\x1a\n": ("png", "image/png"),
}


@dataclass(frozen=True, slots=True)
class StoredPhoto:
    relative_path: str
    content_type: str
    size_bytes: int


class PhotoStorage:
    def __init__(self, upload_dir: str, max_mb: int, clock: Clock) -> None:
        self._root = Path(upload_dir)
        self._max_mb = max_mb
        self._max_bytes = max_mb * 1024 * 1024
        self._clock = clock

    def save(self, stream: BinaryIO) -> StoredPhoto:
        data = stream.read(self._max_bytes + 1)
        if len(data) > self._max_bytes:
            raise PhotoTooLargeError(self._max_mb)
        if not data:
            raise PhotoRejectedError("The photo file is empty.")
        kind = next((kind for magic, kind in SIGNATURES.items() if data.startswith(magic)), None)
        if kind is None:
            raise PhotoRejectedError("Only JPEG and PNG photos can be uploaded.")

        extension, content_type = kind
        folder = f"{self._clock.now():%Y/%m}"
        name = f"{uuid.uuid4().hex}.{extension}"  # random, so a name reveals nothing
        (self._root / folder).mkdir(parents=True, exist_ok=True)
        (self._root / folder / name).write_bytes(data)
        return StoredPhoto(f"{folder}/{name}", content_type, len(data))

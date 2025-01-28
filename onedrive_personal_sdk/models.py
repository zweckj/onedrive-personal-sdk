from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from collections.abc import AsyncIterator
from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro import field_options


@dataclass
class LargeFileChunkUploadResult(DataClassJSONMixin):
    """Result of uploading a large file chunk."""

    expiration_date_time: datetime = field(
        metadata=field_options(alias="expirationDateTime")
    )
    next_expected_ranges: list[str] = field(
        metadata=field_options(alias="nextExpectedRanges")
    )

    @property
    def next_expected_range_start(self) -> int:
        """Get the start of the next expected range."""
        return int(self.next_expected_ranges[0].split("-")[0])


@dataclass
class LargeFileUploadSession(DataClassJSONMixin):
    """A large file upload session."""

    upload_url: str = field(metadata=field_options(alias="uploadUrl"))
    expiration_date_time: datetime = field(
        metadata=field_options(alias="expirationDateTime")
    )
    deferred_commit: bool = False


@dataclass
class FileInfo:
    """Information about a file to upload."""

    name: str
    size: int
    folder_path_id: str
    content_stream: AsyncIterator[bytes]


@dataclass
class UploadBuffer:
    """Buffer for uploading files."""

    buffer: bytearray = field(default_factory=bytearray)
    start_byte: int = 0

    @property
    def length(self) -> int:
        """Get the length of the buffer."""
        return len(self.buffer)


@dataclass
class ItemParentReference(DataClassJSONMixin):
    """Parent reference for an item."""

    id: str
    name: str
    drive_id: str = field(metadata=field_options(alias="driveId"))
    path: str


@dataclass
class Item(DataClassJSONMixin):
    """Describes a OneDrive item (file or folder)."""

    id: str
    name: str
    parent_reference: ItemParentReference = field(
        metadata=field_options(alias="parentReference")
    )
    size: int


@dataclass
class Hashes(DataClassJSONMixin):
    """Hashes for an item."""

    quick_xor_hash: str = field(metadata=field_options(alias="quickXorHash"))
    sha1_hash: str = field(metadata=field_options(alias="sha1Hash"))
    sha256_hash: str = field(metadata=field_options(alias="sha256Hash"))


@dataclass
class File(Item):
    """Describes a file item."""

    hashes: Hashes
    mime_type: str

    @classmethod
    def __pre_deserialize__(cls, d: dict) -> dict:
        file = d["file"]
        d["hashes"] = file["hashes"]
        d["mime_type"] = file["mimeType"]
        return d


@dataclass
class Folder(Item):
    """Describes a folder item."""

    child_count: int

    @classmethod
    def __pre_deserialize__(cls, d: dict) -> dict:
        folder = d["folder"]
        d["child_count"] = folder["childCount"]
        return d

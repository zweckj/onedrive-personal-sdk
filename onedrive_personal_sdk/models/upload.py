"""Models for large file uploads."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime

from mashumaro import field_options
from mashumaro.mixins.json import DataClassJSONMixin


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

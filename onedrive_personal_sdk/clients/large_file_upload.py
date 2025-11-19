"""Large file upload."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from aiohttp import ClientSession
from mashumaro.exceptions import MissingField

from onedrive_personal_sdk.clients.base import OneDriveBaseClient
from onedrive_personal_sdk.const import GRAPH_BASE_URL, ConflictBehavior, HttpMethod
from onedrive_personal_sdk.exceptions import (
    ExpectedRangeNotInBufferError,
    HashMismatchError,
    HttpRequestException,
    OneDriveException,
    UploadSessionExpired,
)
from onedrive_personal_sdk.models.items import File
from onedrive_personal_sdk.models.upload import (
    FileInfo,
    LargeFileChunkUploadResult,
    LargeFileUploadSession,
    UploadBuffer,
)
from onedrive_personal_sdk.util.quick_xor_hash import QuickXorHash

UPLOAD_CHUNK_SIZE = 16 * 320 * 1024  # 5.2MB
MAX_RETRIES = 2
MAX_CHUNK_RETRIES = 6
_LOGGER = logging.getLogger(__name__)


class LargeFileUploadClient(OneDriveBaseClient):
    """Upload large files chunked."""

    _max_retries = MAX_RETRIES
    _upload_chunk_size = UPLOAD_CHUNK_SIZE

    def __init__(
        self,
        get_access_token: Callable[[], Awaitable[str]],
        file: FileInfo,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the upload."""

        super().__init__(get_access_token, session)

        self._file = file

        self._start = 0
        self._buffer = UploadBuffer()
        self._upload_result = LargeFileChunkUploadResult(
            datetime.now(timezone.utc), ["0-"]
        )

    @classmethod
    async def upload(
        cls,
        get_access_token: Callable[[], Awaitable[str]],
        file: FileInfo,
        max_retries: int = MAX_RETRIES,
        upload_chunk_size: int = UPLOAD_CHUNK_SIZE,
        session: ClientSession | None = None,
        defer_commit: bool = False,
        validate_hash: bool = True,
        conflict_behavior: ConflictBehavior = ConflictBehavior.RENAME,
    ) -> File:
        """Upload a file."""
        self = cls(
            get_access_token,
            file,
            session,
        )
        self._upload_chunk_size = upload_chunk_size
        self._max_retries = max_retries

        upload_session = await self.create_upload_session(
            defer_commit, conflict_behavior
        )

        retries = 0
        while retries < self._max_retries:
            try:
                return await self.start_upload(upload_session, validate_hash)
            except (UploadSessionExpired, MissingField):
                _LOGGER.debug("Session expired/not found/broken, restarting")
                self._buffer = UploadBuffer()
                self._upload_result = LargeFileChunkUploadResult(
                    datetime.now(timezone.utc), ["0-"]
                )
                self._start = 0
                retries += 1
            # except ExpectedRangeNotInBufferError:
            #     raise  # TODO: Implement fix range by replaying
        raise OneDriveException("Failed to upload file")

    async def create_upload_session(
        self,
        defer_commit: bool = False,
        conflict_behavior: ConflictBehavior = ConflictBehavior.RENAME,
    ) -> LargeFileUploadSession:
        """Create a large file upload session"""

        content = {
            "item": {"@microsoft.graph.conflictBehavior": conflict_behavior.value},
            "deferCommit": defer_commit,
            "name": self._file.name,
        }

        url = f"{GRAPH_BASE_URL}/me/drive/items/{self._file.folder_path_id}:/{self._file.name}:/createUploadSession"
        response = await self._request_json(HttpMethod.POST, url=url, json=content)
        upload_session = LargeFileUploadSession.from_dict(response)
        upload_session.deferred_commit = defer_commit

        return upload_session

    async def start_upload(
        self, upload_session: LargeFileUploadSession, validate_hash: bool
    ) -> File:
        """Upload the file to the session."""

        retries = 0
        quick_xor_hash = QuickXorHash()
        result = {}

        async for chunk in self._file.content_stream:
            self._buffer.buffer += chunk
            quick_xor_hash.update(chunk)
            if self._buffer.length >= self._upload_chunk_size:
                uploaded_chunks = 0
                while (
                    (self._buffer.length - uploaded_chunks * UPLOAD_CHUNK_SIZE)
                    > self._upload_chunk_size
                ):  # Loop in case the buffer is >= UPLOAD_CHUNK_SIZE * 2
                    slice_start = uploaded_chunks * self._upload_chunk_size
                    try:
                        chunk_result = await self._async_upload_chunk(
                            upload_session.upload_url,
                            self._start,
                            self._start + self._upload_chunk_size - 1,
                            self._buffer.buffer[
                                slice_start : slice_start + self._upload_chunk_size
                            ],
                        )
                    except HttpRequestException as err:
                        _LOGGER.debug(
                            "Error during upload of chunk %s: %s: %s",
                            self._upload_result.next_expected_ranges,
                            err.status_code,
                            err,
                        )
                        retries += 1
                        if retries > MAX_CHUNK_RETRIES:
                            raise
                        if (
                            self._upload_result.expiration_date_time
                            and self._upload_result.expiration_date_time
                            <= datetime.now(timezone.utc)
                        ):
                            _LOGGER.debug("Session expired")
                            raise UploadSessionExpired from err
                        if err.status_code == 404:
                            _LOGGER.debug("Session not found")
                            raise UploadSessionExpired from err
                        # 500 error, wait then retry
                        if int(err.status_code / 100) == 5:
                            await asyncio.sleep(2**retries)
                            continue
                        # range not satisfiable, retry with new range
                        if err.status_code in (409, 416):
                            next_expected_ranges = await self._get_next_expected_ranges(
                                upload_session
                            )
                            # wants same range again, retry
                            if (
                                next_expected_ranges.next_expected_range_start
                                == self._start
                            ):
                                _LOGGER.debug("Retrying same range")
                                continue
                            # it just wants the next regular range
                            if next_expected_ranges.next_expected_range_start == (
                                self._start + self._upload_chunk_size
                            ):
                                _LOGGER.debug("Next range is next regular range")
                                self._upload_result = next_expected_ranges
                            # wants a different range, try to fix it
                            else:
                                _LOGGER.debug(
                                    "Range not satisfiable, at %s, expected: %s",
                                    self._start,
                                    next_expected_ranges.next_expected_range_start,
                                )
                                await self._fix_range(
                                    next_expected_ranges.next_expected_range_start
                                )
                                uploaded_chunks = 0
                                continue
                        else:
                            raise
                    except TimeoutError:
                        _LOGGER.debug("Timeout error, retrying")
                        retries += 1
                        if retries > MAX_CHUNK_RETRIES:
                            raise
                        await asyncio.sleep(2**retries)
                        continue
                    else:
                        if "file" in chunk_result:  # last chunk, no more ranges
                            result = chunk_result
                        else:
                            self._upload_result = LargeFileChunkUploadResult.from_dict(
                                chunk_result
                            )
                            _LOGGER.debug(
                                "Next expected range: %s",
                                self._upload_result.next_expected_ranges,
                            )
                    retries = 0
                    self._start += self._upload_chunk_size
                    uploaded_chunks += 1

                    # returned range is not what we expected, fix range
                    if self._start != (
                        expected_range := self._upload_result.next_expected_range_start
                    ):
                        _LOGGER.debug("Slice start did not expected slice")
                        await self._fix_range(expected_range)
                        uploaded_chunks = 0
                        continue

                self._buffer.buffer = self._buffer.buffer[
                    self._upload_chunk_size * uploaded_chunks :
                ]
                self._buffer.start_byte = self._start

        # upload the remaining bytes
        if self._buffer.buffer:
            _LOGGER.debug("Last chunk")
            # try:
            result = await self._async_upload_chunk(
                upload_session.upload_url,
                self._start,
                self._start + self._buffer.length - 1,
                self._buffer.buffer,
            )
            # except APIError:
            #     await self._commit_file(upload_session)

        if upload_session.deferred_commit:
            file = await self.commit_file(upload_session)
        else:
            file = File.from_dict(result)

        if validate_hash:
            if file.hashes.quick_xor_hash != (hash_b64 := quick_xor_hash.base64()):
                raise HashMismatchError(
                    f"Hash mismatch for {self._file.name}: Online:{file.hashes.quick_xor_hash} != Calculated: {hash_b64}"
                )
            _LOGGER.debug("Hashes match")

        return file

    async def _async_upload_chunk(
        self, upload_url: str, start: int, end: int, chunk_data: bytearray
    ) -> dict:
        """Upload a part to the session."""

        headers: dict[str, str] = {}
        headers["Content-Range"] = f"bytes {start}-{end}/{self._file.size}"
        headers["Content-Length"] = str(len(chunk_data))
        headers["Content-Type"] = "application/octet-stream"
        _LOGGER.debug(headers)
        result = await self._request_json(
            method=HttpMethod.PUT,
            url=upload_url,
            authorize=False,
            headers=headers,
            data=chunk_data,
        )
        return result

    async def commit_file(
        self,
        upload_session: LargeFileUploadSession,
    ) -> File:
        """Commit file manually."""
        _LOGGER.debug("Committing file")

        result = await self._request(
            HttpMethod.POST, upload_session.upload_url, authorize=False
        )
        if result.status != 201:
            raise OneDriveException(f"Failed to commit file, status: {result.status}")
        result_json = await self._request_json(
            HttpMethod.GET,
            f"{GRAPH_BASE_URL}/me/drive/items/{self._file.folder_path_id}:/{self._file.name}:",
        )
        return File.from_dict(result_json)

    async def _fix_range(self, expected_start: int | None) -> None:
        """Move the buffer to the expected range."""
        if expected_start is None:
            # we are at the end
            _LOGGER.debug("Expected range is None, clearing buffer")
            self._buffer.buffer = bytearray()
            return
        if not (
            self._buffer.start_byte
            <= expected_start
            < (self._start + self._buffer.length)
        ):
            raise ExpectedRangeNotInBufferError(expected_start=expected_start)
        _LOGGER.debug("Fixing range to %s", expected_start)
        self._buffer.buffer = self._buffer.buffer[
            (expected_start - self._buffer.start_byte) :
        ]
        self._buffer.start_byte = expected_start
        self._start = expected_start

    async def _get_next_expected_ranges(
        self, upload_session: LargeFileUploadSession
    ) -> LargeFileChunkUploadResult:
        """Query the API for the next expected byte range."""
        _LOGGER.debug("Getting next expected ranges")
        response = await self._request_json(
            HttpMethod.GET, upload_session.upload_url, authorize=False
        )
        upload_result = LargeFileChunkUploadResult.from_dict(response)
        _LOGGER.debug(
            "Next expected range from API: %s",
            (
                ", ".join(upload_result.next_expected_ranges)
                if upload_result.next_expected_ranges
                else "None"
            ),
        )
        return upload_result

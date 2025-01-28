"""Large file upload."""

import asyncio
from datetime import datetime
import logging

from aiohttp import ClientSession

from onedrive_personal_sdk.clients.base import OneDriveBaseClient, TokenProvider
from onedrive_personal_sdk.exceptions import HttpRequestException
from onedrive_personal_sdk.const import HttpMethod, ConflictBehavior, GRAPH_BASE_URL
from onedrive_personal_sdk.models.upload import (
    LargeFileChunkUploadResult,
    FileInfo,
    LargeFileUploadSession,
    UploadBuffer,
)

UPLOAD_CHUNK_SIZE = 16 * 320 * 1024  # 5.2MB
MAX_RETRIES = 5
_LOGGER = logging.getLogger(__name__)


class LargeFileUploadClient(OneDriveBaseClient):
    """Upload large files chunked."""

    def __init__(
        self,
        token_provider: TokenProvider,
        file: FileInfo,
        max_retries: int = MAX_RETRIES,
        upload_chunk_size: int = UPLOAD_CHUNK_SIZE,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the upload."""

        super().__init__(token_provider, session)

        self._file = file
        self._start = 0
        self._buffer = UploadBuffer()
        self._upload_chunk_size = upload_chunk_size
        self._max_retries = max_retries
        self._upload_result = LargeFileChunkUploadResult(datetime.now(), ["0-"])

    async def upload_file(
        self,
        description: str | None = None,
        defer_commit: bool = False,
        conflict_behaviour: ConflictBehavior = ConflictBehavior.FAIL,
    ) -> None:
        """Wrapper for handling the file upload"""

        upload_session = await self._create_upload_session(
            description, defer_commit, conflict_behaviour
        )

        retries = 0
        while retries < self._max_retries:
            try:
                await self._upload_file(upload_session)
            except HttpRequestException as err:
                if err.status_code == 404:
                    _LOGGER.debug("Session not found, restarting")
                    self._buffer = UploadBuffer()
                    self._start = 0
                    retries += 1
                else:
                    raise

    async def _create_upload_session(
        self,
        description: str | None = None,
        defer_commit: bool = False,
        conflict_behaviour: ConflictBehavior = ConflictBehavior.FAIL,
    ) -> LargeFileUploadSession:
        """Create a large file upload session"""
        item = {
            "@microsoft.graph.conflictBehavior": conflict_behaviour.value,
            "name": self._file.name,
            "fileSize": self._file.size,
        }

        if description:
            item["description"] = description

        content = {
            "item": item,
            "deferCommit": defer_commit,
        }

        url = f"{GRAPH_BASE_URL}/me/drive/items/{self._file.folder_path_id}:/{self._file.name}:/createUploadSession"
        response = await self._request_json(HttpMethod.POST, url=url, json=content)
        upload_session = LargeFileUploadSession.from_dict(response)
        upload_session.deferred_commit = defer_commit

        return upload_session

    async def _upload_file(self, upload_session: LargeFileUploadSession) -> None:
        """Upload the file to the session."""

        retries = 0

        async for chunk in self._file.content_stream:
            self._buffer.buffer += chunk
            if self._buffer.length >= self._upload_chunk_size:
                uploaded_chunks = 0
                while (
                    self._buffer.length - uploaded_chunks * UPLOAD_CHUNK_SIZE
                ) > self._upload_chunk_size:  # Loop in case the buffer is >= UPLOAD_CHUNK_SIZE * 2
                    slice_start = uploaded_chunks * self._upload_chunk_size
                    try:
                        self._upload_result = await self._async_upload_chunk(
                            upload_session.upload_url,
                            self._start,
                            self._start + self._upload_chunk_size - 1,
                            self._buffer.buffer[
                                slice_start : slice_start + self._upload_chunk_size
                            ],
                        )
                    except HttpRequestException as err:
                        if upload_session.expiration_date_time <= datetime.now():
                            raise
                        # 500 error, wait then retry
                        if int(err.status_code / 100) == 5:
                            await asyncio.sleep(2**retries)
                        # # 416, range not satisfiable, retry with new range
                        # if err.status_code == 416:
                        #     _LOGGER.debug("Range not satisfiable, retrying")
                        #     await self._fix_range(chunk_data)
                        if err.status_code == 404:
                            _LOGGER.debug("Session not found, restarting")
                            raise
                        retries += 1
                        if retries > self._max_retries:
                            raise
                        continue
                    except TimeoutError:
                        _LOGGER.debug("Timeout error, retrying")
                        retries += 1
                        if retries > self._max_retries:
                            raise
                        continue
                    retries = 0
                    self._start += self._upload_chunk_size

                    # # returned range is not what we expected, fix range
                    # if self._start != (
                    #     expected_range := int(
                    #         upload_result.next_expected_ranges[0].split("-")[0]
                    #     )
                    # ):
                    #     _LOGGER.debug("Slice start did not expected slice")
                    #     await self._fix_range(chunk_data, expected_range)
                    #     continue

                    uploaded_chunks += 1
                self._buffer.buffer = self._buffer.buffer[
                    self._upload_chunk_size * uploaded_chunks :
                ]
                self._buffer.start_byte = self._start

        # upload the remaining bytes
        if self._buffer.buffer:
            _LOGGER.debug("Last chunk")
            # try:
            await self._async_upload_chunk(
                upload_session.upload_url,
                self._start,
                self._start + self._buffer.length - 1,
                self._buffer.buffer,
            )
            # except APIError:
            #     await self._commit_file(upload_session)
        # if upload_session.deferred_commit:
        #     await self.commit_file(upload_session)

    async def _async_upload_chunk(
        self, upload_url: str, start: int, end: int, chunk_data: bytearray
    ) -> LargeFileChunkUploadResult:
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

        chunk_result = LargeFileChunkUploadResult.from_dict(result)
        _LOGGER.debug(
            "Next expected range: %s-", chunk_result.next_expected_range_start
        )
        return chunk_result

    # async def _get_next_expected_ranges(self) -> list[int]:
    #     """Query the API for the next expected byte range."""
    #     response = await self._request_json(HttpMethod.GET, self._upload_url, authorize=False)
    #     expected_ranges = cast(list[str], response["nextExpectedRanges"])
    #     return [int(expected_range.split("-")[0]) for expected_range in expected_ranges]

    # async def _fix_range(
    #     self, chunk_data: bytes, expected_start: int | None = None
    # ) -> None:
    #     """Move the buffer to the expected range."""
    #     if expected_start is None:
    #         next_expected_ranges = await self._get_next_expected_ranges()
    #         expected_start = next_expected_ranges[0]
    #     if not (
    #         self._buffer_start_byte
    #         <= expected_start
    #         < (self._start + self._buffer_size)
    #     ):
    #         raise Exception()
    #     self._buffer = chunk_data[expected_start:]
    #     self._buffer_size = len(self._buffer[0])

    async def _commit_file(
        self,
        upload_session: LargeFileUploadSession,
        conflict_behaviour: ConflictBehavior = ConflictBehavior.FAIL,
    ) -> None:
        """Commit file manually."""

        url = f"https://graph.microsoft.com/v1.0/me/drive/{self._file.folder_path_id}:"
        content = {
            "name": self._file.name,
            "@microsoft.graph.conflictBehavior": conflict_behaviour,
            "@microsoft.graph.sourceUrl": upload_session.upload_url,
        }
        await self._request_json(HttpMethod.PUT, url, json=content)

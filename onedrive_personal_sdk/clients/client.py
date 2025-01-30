"""The OneDrive API client."""

import logging
from collections.abc import AsyncIterator

from aiohttp import StreamReader, ClientTimeout

from onedrive_personal_sdk.clients.base import OneDriveBaseClient
from onedrive_personal_sdk.const import GRAPH_BASE_URL, ConflictBehavior, HttpMethod
from onedrive_personal_sdk.exceptions import (
    NotFoundError,
    OneDriveException,
)
from onedrive_personal_sdk.models.items import AppRoot, File, Folder, ItemUpdate

_LOGGER = logging.getLogger(__name__)


class OneDriveClient(OneDriveBaseClient):
    """OneDrive API client."""

    def _dict_to_item(self, item: dict) -> File | Folder:
        if "folder" in item:
            return Folder.from_dict(item)
        if "file" in item:
            return File.from_dict(item)
        raise OneDriveException("Unknown item type")

    async def get_drive_item(self, path_or_id: str) -> File | Folder:
        """Get a drive item by path."""
        result = await self._request_json(
            HttpMethod.GET, f"{GRAPH_BASE_URL}/me/drive/items/{path_or_id}"
        )
        return self._dict_to_item(result)

    async def get_approot(self) -> AppRoot:
        """Get the approot."""
        result = await self._request_json(
            HttpMethod.GET, f"{GRAPH_BASE_URL}/me/drive/special/approot:"
        )
        return AppRoot.from_dict(result)

    async def list_drive_items(self, path_or_id: str) -> list[File | Folder]:
        """List items in a drive."""

        response = await self._request_json(
            HttpMethod.GET, f"{GRAPH_BASE_URL}/me/drive/items/{path_or_id}/children"
        )
        return [self._dict_to_item(item) for item in response["value"]]

    async def delete_drive_item(self, path_or_id: str) -> None:
        """Delete items in a drive."""

        await self._request_json(
            HttpMethod.DELETE,
            f"{GRAPH_BASE_URL}/me/drive/items/{path_or_id}",
            content_type=None,
        )

    async def download_drive_item(
        self, path_or_id: str, timeout: ClientTimeout = ClientTimeout()
    ) -> StreamReader:
        """Download items in a drive."""
        response = await self._request(
            HttpMethod.GET,
            f"{GRAPH_BASE_URL}/me/drive/items/{path_or_id}/content",
            timeout=timeout,
        )
        return response.content

    async def update_drive_item(
        self, path_or_id: str, data: ItemUpdate
    ) -> File | Folder:
        """Update items in a drive."""
        response = await self._request_json(
            HttpMethod.PATCH,
            f"{GRAPH_BASE_URL}/me/drive/items/{path_or_id}",
            json=data.to_dict(),
        )
        return self._dict_to_item(response)

    async def create_folder(
        self,
        parent_id: str,
        name: str,
        fail_if_exists: bool = False,
    ) -> Folder:
        """Create a folder in a drive."""
        try:
            item = await self.get_drive_item(f"{parent_id}:/{name}:")
        except NotFoundError:
            _LOGGER.debug("Creating folder %s in %s", name, parent_id)
            response = await self._request_json(
                HttpMethod.POST,
                f"{GRAPH_BASE_URL}/me/drive/items/{parent_id}/children",
                json={
                    "name": name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": ConflictBehavior.FAIL.value,
                },
            )
            return Folder.from_dict(response)
        if not isinstance(item, Folder):
            raise OneDriveException("Item exists but is not a folder")
        _LOGGER.debug("Folder %s already exists in %s", name, parent_id)
        if fail_if_exists:
            raise OneDriveException("Folder already exists")
        return item
        

    async def upload_file(
        self,
        parent_id: str,
        file_name: str,
        file_stream: AsyncIterator[bytes],
        timeout: ClientTimeout = ClientTimeout(),
    ) -> File:
        """Upload a file to a drive. Max 250MB file size."""
        headers = {"Content-Type": "text/plain"}
        response = await self._request_json(
            HttpMethod.PUT,
            f"{GRAPH_BASE_URL}/me/drive/items/{parent_id}:/{file_name}:/content",
            data=file_stream,
            headers=headers,
            timeout=timeout,
        )
        return File.from_dict(response)

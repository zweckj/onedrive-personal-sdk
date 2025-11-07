"""The OneDrive API client."""

import logging
from typing import Any

from aiohttp import StreamReader, ClientTimeout

from onedrive_personal_sdk.clients.base import OneDriveBaseClient
from onedrive_personal_sdk.const import GRAPH_BASE_URL, ConflictBehavior, HttpMethod
from onedrive_personal_sdk.exceptions import (
    NotFoundError,
    OneDriveException,
)
from onedrive_personal_sdk.models.items import AppRoot, File, Folder, ItemUpdate, Drive

_LOGGER = logging.getLogger(__name__)


class OneDriveClient(OneDriveBaseClient):
    """OneDrive API client."""

    def _dict_to_item(self, item: dict) -> File | Folder:
        if "folder" in item:
            return Folder.from_dict(item)
        if "file" in item:
            return File.from_dict(item)
        raise OneDriveException("Unknown item type")

    async def get_drive(self) -> Drive:
        """Get the drive resource."""
        result = await self._request_json(HttpMethod.GET, f"{GRAPH_BASE_URL}/me/drive")
        return Drive.from_dict(result)

    async def get_drive_item(self, path_or_id: str) -> File | Folder:
        """Get a drive item by path."""
        result = await self._request_json(
            HttpMethod.GET, f"{GRAPH_BASE_URL}/me/drive/items/{path_or_id}"
        )
        return self._dict_to_item(result)

    async def get_approot(self) -> AppRoot:
        """Get the approot."""
        result = await self._request_json(
            HttpMethod.GET, f"{GRAPH_BASE_URL}/me/drive/special/approot"
        )
        return AppRoot.from_dict(result)

    async def list_drive_items(self, path_or_id: str) -> list[File | Folder]:
        """List items in a drive."""
        items: list[File | Folder] = []
        next_link = f"{GRAPH_BASE_URL}/me/drive/items/{path_or_id}/children"
        while next_link:
            response = await self._request_json(HttpMethod.GET, next_link)
            items.extend(self._dict_to_item(item) for item in response["value"])
            next_link = response.get("@odata.nextLink", "")
        return items

    async def delete_drive_item(
        self, path_or_id: str, delete_permanently: bool = False
    ) -> None:
        """Delete items in a drive."""
        if delete_permanently:
            await self._request(
                HttpMethod.POST,
                f"{GRAPH_BASE_URL}/me/drive/items/{path_or_id}/permanentDelete",
                data={},
            )
        else:
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
        response = await self._request(
            HttpMethod.PATCH,
            f"{GRAPH_BASE_URL}/me/drive/items/{path_or_id}",
            json=data.to_dict(),
        )
        if response.status == 204:
            raise OneDriveException("Item update had no effect")
        json = await response.json()
        return self._dict_to_item(json)

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
        data: Any,
        timeout: ClientTimeout = ClientTimeout(),
    ) -> File:
        """Upload a file to a drive. Max 250MB file size."""
        headers = {"Content-Type": "text/plain"}
        response = await self._request_json(
            HttpMethod.PUT,
            f"{GRAPH_BASE_URL}/me/drive/items/{parent_id}:/{file_name}:/content",
            data=data,
            headers=headers,
            timeout=timeout,
        )
        return File.from_dict(response)

"""The OneDrive API client."""

from typing import cast
from collections.abc import AsyncIterator
import logging

from aiohttp import StreamReader

from onedrive_personal_sdk.clients.base import OneDriveBaseClient
from onedrive_personal_sdk.const import GRAPH_BASE_URL, ConflictBehavior, HttpMethod
from onedrive_personal_sdk.exceptions import OneDriveException, HttpRequestException
from onedrive_personal_sdk.models.items import File, Folder, ItemUpdate

_LOGGER = logging.getLogger(__name__)


class OneDriveClient(OneDriveBaseClient):
    """OneDrive API client."""

    def _dict_to_item(self, item: dict) -> File | Folder:
        if "folder" in item:
            return Folder.from_dict(item)
        if "file" in item:
            return File.from_dict(item)
        raise OneDriveException("Unknown item type")

    async def get_drive_item(self, path: str) -> File | Folder:
        """Get a drive item by path."""
        result = await self._request_json(
            HttpMethod.GET, GRAPH_BASE_URL + f"/me/drive/{path}:"
        )
        return self._dict_to_item(result)

    async def get_approot(self) -> Folder:
        """Get the approot."""
        return cast(Folder, await self.get_drive_item("special/approot"))

    async def list_drive_items(self, item_id: str) -> list[File | Folder]:
        """List items in a drive."""
        response = await self._request_json(
            HttpMethod.GET, GRAPH_BASE_URL + f"/me/drive/items/{item_id}/children"
        )
        return [self._dict_to_item(item) for item in response["value"]]

    async def delete_drive_item(self, path: str) -> None:
        """Delete items in a drive."""
        await self._request_json(
            HttpMethod.DELETE,
            GRAPH_BASE_URL + f"/me/drive/items/{path}:",
            content_type=None,
        )

    async def download_drive_item(self, path: str) -> StreamReader:
        """Download items in a drive."""
        response = await self._request(
            HttpMethod.GET, GRAPH_BASE_URL + f"/me/drive/items/{path}:/content"
        )
        return response.content

    async def update_drive_item(self, item_id: str, data: ItemUpdate) -> File | Folder:
        """Update items in a drive."""
        response = await self._request_json(
            HttpMethod.PATCH,
            GRAPH_BASE_URL + f"/me/drive/items/{item_id}",
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
            await self.get_drive_item(f"{parent_id}:/{name}")
        except HttpRequestException as err:
            if err.status_code == 404:
                _LOGGER.debug("Creating folder %s in %s", name, parent_id)
                response = await self._request_json(
                    HttpMethod.POST,
                    GRAPH_BASE_URL + f"/me/drive/items/{parent_id}/children",
                    json={
                        "name": name,
                        "folder": {},
                        "@microsoft.graph.conflictBehavior": ConflictBehavior.FAIL.value,
                    },
                )
                return Folder.from_dict(response)
            raise
        _LOGGER.debug("Folder %s already exists in %s", name, parent_id)
        if fail_if_exists:
            raise OneDriveException("Folder already exists")

    async def upload_file(
        self,
        parent_id: str,
        file_name: str,
        file_stream: AsyncIterator[bytes],
    ) -> File:
        """Upload a file to a drive. Max 250MB file size."""
        headers = {"Content-Type": "text/plain"}
        response = await self._request_json(
            HttpMethod.PUT,
            GRAPH_BASE_URL + f"/me/drive/items/{parent_id}:/{file_name}:/content",
            data=file_stream,
            headers=headers,
        )
        return File.from_dict(response)

"""The OneDrive API client."""

from aiohttp import StreamReader
from typing import cast

from .base import OneDriveBaseClient
from .const import GRAPH_BASE_URL, ConflictBehavior, HttpMethod
from .exceptions import OneDriveException

from .models import File, Folder


class OneDriveClient(OneDriveBaseClient):
    """OneDrive API client."""

    async def get_drive_item(self, path: str) -> File | Folder:
        """Get a drive item by path."""
        result = await self._request_json(
            HttpMethod.GET, GRAPH_BASE_URL + f"/me/drive/{path}:"
        )
        if "folder" in result:
            return Folder.from_dict(result)
        if "file" in result:
            return File.from_dict(result)
        raise OneDriveException("Unknown item type")

    async def get_approot(self) -> Folder:
        """Get the approot."""
        return cast(Folder, await self.get_drive_item("special/approot"))

    async def list_drive_items(self, item_id: str) -> dict:
        """List items in a drive."""
        return await self._request_json(
            HttpMethod.GET, GRAPH_BASE_URL + f"/me/drive/items/{item_id}/children"
        )

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

    async def update_drive_item(self, item_id: str, data: dict) -> dict:
        """Update items in a drive."""
        return await self._request_json(
            HttpMethod.PATCH, GRAPH_BASE_URL + f"/me/drive/items/{item_id}", json=data
        )

    async def create_folder(
        self,
        parent_id: str,
        name: str,
        conflict_behaviour: ConflictBehavior = ConflictBehavior.RENAME,
    ) -> dict:
        """Create a folder in a drive."""
        return await self._request_json(
            HttpMethod.POST,
            GRAPH_BASE_URL + f"/me/drive/items/{parent_id}/children",
            json={
                "name": name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": conflict_behaviour.value,
            },
        )

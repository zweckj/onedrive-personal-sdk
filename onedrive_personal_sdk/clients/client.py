"""The OneDrive API client."""

from aiohttp import StreamReader
from typing import cast

from onedrive_personal_sdk.clients.base import OneDriveBaseClient
from onedrive_personal_sdk.const import GRAPH_BASE_URL, ConflictBehavior, HttpMethod
from onedrive_personal_sdk.exceptions import OneDriveException

from onedrive_personal_sdk.models.items import File, Folder, ItemUpdate


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
            HttpMethod.PATCH, GRAPH_BASE_URL + f"/me/drive/items/{item_id}", json=data.to_dict()
        )
        return self._dict_to_item(response)

    async def create_folder(
        self,
        parent_id: str,
        name: str,
        conflict_behaviour: ConflictBehavior = ConflictBehavior.RENAME,
    ) -> Folder:
        """Create a folder in a drive."""
        response = await self._request_json(
            HttpMethod.POST,
            GRAPH_BASE_URL + f"/me/drive/items/{parent_id}/children",
            json={
                "name": name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": conflict_behaviour.value,
            },
        )
        return Folder.from_dict(response)

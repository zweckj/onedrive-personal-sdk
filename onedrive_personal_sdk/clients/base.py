"""OneDrive base API client."""

from collections.abc import Callable, Awaitable

from aiohttp import ClientError, ClientResponse, ClientSession, ConnectionTimeoutError

from onedrive_personal_sdk.const import HttpMethod
from onedrive_personal_sdk.exceptions import (
    AuthenticationError,
    ClientException,
    HttpRequestException,
    NotFoundError,
    TimeoutException,
)


class OneDriveBaseClient:
    """OneDrive base API client."""

    def __init__(
        self,
        get_access_token: Callable[[], Awaitable[str]],
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the client."""
        self._get_access_token = get_access_token
        self._session = session or ClientSession()

    async def _request(
        self, method: HttpMethod, url: str, authorize: bool = True, **kwargs
    ) -> ClientResponse:
        """Make a request to the API."""
        headers = kwargs.pop("headers", {})
        if authorize:
            token = await self._get_access_token()
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = await self._session.request(
                method.value, url, headers=headers, **kwargs
            )
        except ConnectionTimeoutError as err:
            raise TimeoutException from err
        except ClientError as err:
            raise ClientException from err

        if response.status >= 400:
            if response.status == 403:
                raise AuthenticationError(response.status, await response.text())
            if response.status == 404:
                raise NotFoundError(response.status, await response.text())
            raise HttpRequestException(response.status, await response.text())
        return response

    async def _request_json(
        self,
        method: HttpMethod,
        url: str,
        authorize: bool = True,
        content_type: str | None = "application/json",
        **kwargs,
    ) -> dict:
        """Make a request to the API and get json."""
        response = await self._request(method, url, authorize, **kwargs)
        return await response.json(content_type=content_type)

"""OneDrive base API client."""

from abc import abstractmethod

from aiohttp import ClientError, ClientResponse, ClientSession

from onedrive_personal_sdk.const import HttpMethod
from onedrive_personal_sdk.exceptions import (
    AuthenticationError,
    ClientException,
    HttpRequestException,
    NotFoundError,
)


class TokenProvider:
    """Class that provides auth tokens."""

    @abstractmethod
    def async_get_access_token(self) -> str:
        """Get the access token."""


class OneDriveBaseClient:
    """OneDrive base API client."""

    def __init__(
        self, token_provider: TokenProvider, session: ClientSession | None = None
    ) -> None:
        """Initialize the client."""
        self._token_provider = token_provider
        self._session = session or ClientSession()

    async def _request(
        self, method: HttpMethod, url: str, authorize: bool = True, **kwargs
    ) -> ClientResponse:
        """Make a request to the API."""
        headers = kwargs.pop("headers", {})
        if authorize:
            token = self._token_provider.async_get_access_token()
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = await self._session.request(
                method.value, url, headers=headers, **kwargs
            )
        except ClientError as err:
            raise ClientException from err

        if response.status >= 400:
            if response.status in (401, 403):
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

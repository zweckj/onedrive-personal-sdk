from aiohttp import ClientError


class OneDriveException(Exception):
    """Base exception for OneDrive exceptions."""


class HttpRequestException(OneDriveException):
    """Exception raised when an HTTP request fails."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.status_code = status_code


class ClientException(ClientError, OneDriveException):
    """Exception raised when an API request fails."""

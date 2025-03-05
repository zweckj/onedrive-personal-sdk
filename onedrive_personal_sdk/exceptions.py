"""Exceptions for OneDrive."""

from aiohttp import ClientError


class OneDriveException(Exception):
    """Base exception for OneDrive exceptions."""


class HttpRequestException(OneDriveException):
    """Exception raised when an HTTP request fails."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(HttpRequestException):
    """Exception raised when authentication fails."""


class NotFoundError(HttpRequestException):
    """Exception raised when item is not found."""

class TimeoutException(TimeoutError, OneDriveException):
    """Exception raised when an API request times out."""

class ClientException(ClientError, OneDriveException):
    """Exception raised when an API request fails."""


class HashMismatchError(OneDriveException):
    """Exception raised when the hash of a file does not match."""


class ExpectedRangeNotInBufferError(OneDriveException):
    """Exception raised when the expected range is not in the buffer."""

    def __init__(self, expected_start: int) -> None:
        """Initialize the exception."""
        super().__init__(f"Expected range '{expected_start}-' not in buffer")
        self.expected_start = expected_start


class UploadSessionExpired(OneDriveException):
    """Exception raised when the upload session has expired."""

from enum import StrEnum

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

class ConflictBehavior(StrEnum):
    """Conflict behavior."""
    FAIL = "fail"
    REPLACE = "replace"
    RENAME = "rename"

class HttpMethod(StrEnum):
    """HTTP methods."""
    PUT = "PUT"
    POST = "POST"
    PATCH = "PATCH"
    DELETE = "DELETE"
    GET = "GET"
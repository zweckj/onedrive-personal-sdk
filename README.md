# OneDrive Personal SDK

OneDrive Personal SDK is a Python library for interacting with a personal OneDrive through the Graph API.

# Usage

## Getting an authentication token

The library is built to support different token providers. To add authentication to the library you need to define a `get_access_token` method and pass that to the library.

To use `msal` as a token provider you can create that function like the following:

```python
from msal import PublicClientApplication

app = PublicClientApplication(
    "Client ID",
    authority="https://login.microsoftonline.com/consumers",
)


async def get_access_token(self) -> str:
    result = app.acquire_token_interactive(
        scopes=[
            "Files.ReadWrite.All",
        ]
    )
    return result["access_token"]
```

## Creating a client

To create a client you need to provide a function to retrieve an access token.

```python
from onedrive_personal_sdk import OneDriveClient

client = OneDriveClient(get_access_token)

# can also be created with a custom aiohttp session
client = OneDriveClient(get_access_token, session=session)
```

# Calling the API

The client provides methods to interact with the OneDrive API. The methods are async and return the response from the API. Most methods accept item ids or paths as arguments.

```python


root = await client.get_drive_item("root") # Get the root folder
item = await client.get_drive_item("root:/path/to/item:") # Get an item by path
item = await client.get_drive_item(item.id) # Get an item by id

folder = await client.get_drive_item("root:/path/to/folder:") # Get a folder

# List children of a folder
children = await client.list_children("root:/path/to/folder:")
children = await client.list_children(folder.id)

```

# Uploading files

Smaller files (<250MB) can be uploaded with the `upload` method. All files need to be provided as AsyncIterators. Such a generator can be created from `aiofiles`.

```python
import aiofiles
from collections.abc import AsyncIterator

async def file_reader(file_path: str) -> AsyncIterator[bytes]:
    async with aiofiles.open(file_path, "rb") as f:
        while True:
            chunk = await f.read(1024)  # Read in chunks of 1024 bytes
            if not chunk:
                break
            yield chunk
```

```python
await client.upload_file("root:/TestFolder", "test.txt", file_reader("test.txt"))
```

Larger files (and small files as well) can be uploaded with a `LargeFileUploadClient`. The client will handle the upload in chunks.

```python
import os
from onedrive_personal_sdk import LargeFileUploadClient
from onedrive_personal_sdk.models.upload FileInfo

filename = "testfile.txt"
size = os.path.getsize(filename)

file = FileInfo(
    name=filename,
    size=size,
    folder_path_id="root",
    content_stream=file_reader(filename),
)
file = await LargeFileUploadClient.upload(auth_provider, file)
```

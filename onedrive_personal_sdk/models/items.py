"""Models for OneDrive drive items."""

from dataclasses import dataclass, field

from mashumaro import field_options
from mashumaro.mixins.json import DataClassJSONMixin


@dataclass
class ItemParentReference(DataClassJSONMixin):
    """Parent reference for an item."""

    id: str
    drive_id: str = field(metadata=field_options(alias="driveId"))
    path: str
    name: str | None = None


@dataclass
class Item(DataClassJSONMixin):
    """Describes a OneDrive item (file or folder)."""

    id: str
    name: str
    parent_reference: ItemParentReference = field(
        metadata=field_options(alias="parentReference")
    )
    size: int


@dataclass
class Hashes(DataClassJSONMixin):
    """Hashes for an item."""

    quick_xor_hash: str | None = field(
        metadata=field_options(alias="quickXorHash"), default=None
    )
    sha1_hash: str | None = field(
        metadata=field_options(alias="sha1Hash"), default=None
    )
    sha256_hash: str | None = field(
        metadata=field_options(alias="sha256Hash"), default=None
    )


@dataclass
class File(Item):
    """Describes a file item."""

    hashes: Hashes
    mime_type: str
    description: str | None = None

    @classmethod
    def __pre_deserialize__(cls, d: dict) -> dict:
        file = d["file"]
        d["hashes"] = file["hashes"]
        d["mime_type"] = file["mimeType"]
        return d


@dataclass
class Folder(Item):
    """Describes a folder item."""

    child_count: int
    description: str | None = None

    @classmethod
    def __pre_deserialize__(cls, d: dict) -> dict:
        folder = d["folder"]
        d["child_count"] = folder["childCount"]
        return d


@dataclass
class ItemOwner(DataClassJSONMixin):
    """Owner of an item."""

    id: str
    email: str
    display_name: str = field(metadata=field_options(alias="displayName"))


@dataclass
class AppRoot(Item):
    """Describes a folder item."""

    child_count: int
    owner: ItemOwner

    @classmethod
    def __pre_deserialize__(cls, d: dict) -> dict:
        folder = d["folder"]
        d["child_count"] = folder["childCount"]
        shared = d["shared"]
        owner = shared["owner"]
        user = owner["user"]
        d["owner"] = user
        return d


@dataclass
class ItemUpdate(DataClassJSONMixin):
    """Update data for an item."""

    name: str | None = None
    description: str | None = None
    parent_reference: ItemParentReference | None = None

    def __post_serialize__(self, d: dict) -> dict:
        return {k: v for k, v in d.items() if v is not None}

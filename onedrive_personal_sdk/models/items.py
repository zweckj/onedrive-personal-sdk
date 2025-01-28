"""Models for OneDrive drive items."""

from dataclasses import dataclass, field
from mashumaro import field_options
from mashumaro.mixins.json import DataClassJSONMixin


@dataclass
class ItemParentReference(DataClassJSONMixin):
    """Parent reference for an item."""

    id: str
    name: str
    drive_id: str = field(metadata=field_options(alias="driveId"))
    path: str


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

    quick_xor_hash: str = field(metadata=field_options(alias="quickXorHash"))
    sha1_hash: str = field(metadata=field_options(alias="sha1Hash"))
    sha256_hash: str = field(metadata=field_options(alias="sha256Hash"))


@dataclass
class File(Item):
    """Describes a file item."""

    hashes: Hashes
    mime_type: str

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

    @classmethod
    def __pre_deserialize__(cls, d: dict) -> dict:
        folder = d["folder"]
        d["child_count"] = folder["childCount"]
        return d

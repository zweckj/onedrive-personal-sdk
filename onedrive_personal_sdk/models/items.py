"""Models for OneDrive drive items."""

from __future__ import annotations

from dataclasses import dataclass, field

from mashumaro import field_options
from mashumaro.mixins.json import DataClassJSONMixin

from onedrive_personal_sdk.const import DriveState, DriveType


@dataclass(kw_only=True)
class ItemParentReference(DataClassJSONMixin):
    """Parent reference for an item."""

    id: str | None = None
    drive_id: str = field(metadata=field_options(alias="driveId"))
    path: str | None = None
    name: str | None = None


@dataclass(kw_only=True)
class Item(DataClassJSONMixin):
    """Describes a OneDrive item (file or folder)."""

    id: str
    name: str
    parent_reference: ItemParentReference = field(
        metadata=field_options(alias="parentReference")
    )
    created_by: IdentitySet = field(metadata=field_options(alias="createdBy"))
    size: int | None = None
    description: str | None = None


@dataclass(kw_only=True)
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


@dataclass(kw_only=True)
class File(Item):
    """Describes a file item."""

    hashes: Hashes
    mime_type: str | None = None

    @classmethod
    def __pre_deserialize__(cls, d: dict) -> dict:
        file: dict = d.get("file", {})
        d["hashes"] = file.get("hashes", {})
        d["mime_type"] = file.get("mimeType", None)
        return d


@dataclass(kw_only=True)
class Folder(Item):
    """Describes a folder item."""

    child_count: int | None = None

    @classmethod
    def __pre_deserialize__(cls, d: dict) -> dict:
        folder: dict = d.get("folder", {})
        d["child_count"] = folder.get("childCount", None)
        return d


@dataclass(kw_only=True)
class EntraEntity(DataClassJSONMixin):
    """Entity data."""

    id: str | None = None
    display_name: str | None = field(
        metadata=field_options(alias="displayName"), default=None
    )


@dataclass(kw_only=True)
class Application(EntraEntity):
    """Application data."""


@dataclass(kw_only=True)
class User(EntraEntity):
    """Owner of an item."""

    email: str | None = None


@dataclass(kw_only=True)
class IdentitySet(DataClassJSONMixin):
    """Owner of an item."""

    user: User | None = None
    application: Application | None = None


@dataclass(kw_only=True)
class AppRoot(Folder):
    """Describes a folder item."""


@dataclass(kw_only=True)
class ItemUpdate(DataClassJSONMixin):
    """Update data for an item."""

    name: str | None = None
    description: str | None = None
    parent_reference: ItemParentReference | None = None

    def __post_serialize__(self, d: dict) -> dict:
        return {k: v for k, v in d.items() if v is not None}

@dataclass(kw_only=True)
class DriveQuota(DataClassJSONMixin):
    """Drive quota data."""

    deleted: int
    remaining: int
    state: DriveState
    total: int
    used: int

@dataclass(kw_only=True)
class Drive(DataClassJSONMixin):
    """Drive data."""

    id: str
    drive_type: DriveType = field(metadata=field_options(alias="driveType"), default=DriveType.PERSONAL)
    name: str | None = None
    owner: IdentitySet | None = None
    quota: DriveQuota | None = None
"""Tests for item model serialization."""

import pytest

from onedrive_personal_sdk.models.items import ItemParentReference, ItemUpdate


class TestItemUpdateSerialization:
    """Tests for ItemUpdate serialization."""

    def test_empty_item_update_serializes_to_empty_dict(self) -> None:
        """Empty ItemUpdate should serialize to empty dict."""
        update = ItemUpdate()
        assert update.to_dict() == {}

    def test_item_update_with_name_only(self) -> None:
        """ItemUpdate with only name should serialize correctly."""
        update = ItemUpdate(name="new_name")
        assert update.to_dict() == {"name": "new_name"}

    def test_item_update_with_description_only(self) -> None:
        """ItemUpdate with only description should serialize correctly."""
        update = ItemUpdate(description="new description")
        assert update.to_dict() == {"description": "new description"}

    def test_item_update_with_parent_reference_uses_camel_case(self) -> None:
        """ItemUpdate with parent_reference should serialize parentReference in camelCase."""
        ref = ItemParentReference(id="parent_id", drive_id="drive123")
        update = ItemUpdate(parent_reference=ref)
        result = update.to_dict()

        # Key should be camelCase 'parentReference', not snake_case 'parent_reference'
        assert "parentReference" in result
        assert "parent_reference" not in result
        # Nested driveId should also be camelCase
        assert "driveId" in result["parentReference"]
        assert "drive_id" not in result["parentReference"]

    def test_item_update_filters_none_values(self) -> None:
        """ItemUpdate should filter out None values from serialized output."""
        update = ItemUpdate(name="test", description=None)
        result = update.to_dict()
        assert result == {"name": "test"}
        assert "description" not in result

    def test_item_update_all_fields(self) -> None:
        """ItemUpdate with all fields should serialize correctly."""
        ref = ItemParentReference(id="parent_id", drive_id="drive123", path="/path")
        update = ItemUpdate(name="test", description="desc", parent_reference=ref)
        result = update.to_dict()

        assert result == {
            "name": "test",
            "description": "desc",
            "parentReference": {"id": "parent_id", "driveId": "drive123", "path": "/path"},
        }


class TestItemParentReferenceSerialization:
    """Tests for ItemParentReference serialization."""

    def test_serializes_drive_id_as_camel_case(self) -> None:
        """ItemParentReference should serialize drive_id as driveId."""
        ref = ItemParentReference(id="parent_id", drive_id="drive123")
        result = ref.to_dict()

        assert "driveId" in result
        assert "drive_id" not in result
        assert result["driveId"] == "drive123"

    def test_filters_none_values(self) -> None:
        """ItemParentReference should filter out None values."""
        ref = ItemParentReference(id="parent_id", drive_id="drive123")
        result = ref.to_dict()

        # path and name are None by default and should be filtered out
        assert "path" not in result
        assert "name" not in result
        assert result == {"id": "parent_id", "driveId": "drive123"}

    def test_includes_non_none_optional_fields(self) -> None:
        """ItemParentReference should include optional fields when set."""
        ref = ItemParentReference(
            id="parent_id", drive_id="drive123", path="/root/folder", name="folder"
        )
        result = ref.to_dict()

        assert result == {
            "id": "parent_id",
            "driveId": "drive123",
            "path": "/root/folder",
            "name": "folder",
        }


class TestItemParentReferenceDeserialization:
    """Tests for ItemParentReference deserialization."""

    def test_deserializes_from_camel_case(self) -> None:
        """ItemParentReference should deserialize from camelCase API response."""
        api_response = {
            "id": "item123",
            "driveId": "drive456",
            "path": "/root/folder",
            "name": "folder",
        }
        ref = ItemParentReference.from_dict(api_response)

        assert ref.id == "item123"
        assert ref.drive_id == "drive456"
        assert ref.path == "/root/folder"
        assert ref.name == "folder"

    def test_deserializes_minimal_response(self) -> None:
        """ItemParentReference should deserialize minimal API response."""
        api_response = {"driveId": "drive456"}
        ref = ItemParentReference.from_dict(api_response)

        assert ref.id is None
        assert ref.drive_id == "drive456"
        assert ref.path is None
        assert ref.name is None

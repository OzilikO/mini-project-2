"""Library Management System - Custom OOP Classes & Collection.

EE 471 Mini Project #2 / Week 4 Foundation.
Defines domain models (MediaItem, Book, DVD), custom exceptions,
and LibraryCollection with CRUD methods, auto-incrementing non-reusable IDs,
filtering, and dictionary serialization.
"""

from typing import Any, Dict, List, Optional


class ItemNotFoundError(Exception):
    """Raised when an item with the requested ID does not exist in the collection."""
    pass


class ItemStateError(Exception):
    """Raised when an operation is invalid for the item's current availability state."""
    pass


class MediaItem:
    """Represents a generic item in a library collection."""

    def __init__(self, title: str, author: str, is_available: bool = True):
        """Initialize a media item with metadata, availability status, and unassigned id."""
        self.id: Optional[int] = None
        self.title: str = title
        self.author: str = author
        self.is_available: bool = is_available

    def checkout(self) -> str:
        """Mark the item as checked out if currently available.

        Raises:
            ItemStateError: If the item is already checked out.
        """
        if not self.is_available:
            raise ItemStateError("Item is already checked out")
        self.is_available = False
        return "Successful checkout"

    def return_item(self) -> str:
        """Mark the item as returned / available.

        Raises:
            ItemStateError: If the item is not currently checked out.
        """
        if self.is_available:
            raise ItemStateError("Item is not checked out")
        self.is_available = True
        return "Successful return"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the media item to a dictionary."""
        return {
            "id": self.id,
            "type": "media_item",
            "title": self.title,
            "author": self.author,
            "is_available": self.is_available,
        }

    def __str__(self) -> str:
        """Return a formatted string displaying ID, title, author, and status."""
        status = "Available" if self.is_available else "Checked Out"
        id_str = f"#{self.id} " if self.id is not None else ""
        return f"{id_str}{self.title} by {self.author} [{status}]"


class Book(MediaItem):
    """Represents a book in the library collection with page count tracking."""

    def __init__(self, title: str, author: str, page_count: int, is_available: bool = True):
        """Initialize a book instance including page count."""
        super().__init__(title, author, is_available)
        self.page_count: int = page_count

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the book to a dictionary with type 'book' and page_count."""
        data = super().to_dict()
        data["type"] = "book"
        data["page_count"] = self.page_count
        return data

    def __str__(self) -> str:
        """Return formatted string containing page count."""
        status = "Available" if self.is_available else "Checked Out"
        id_str = f"#{self.id} " if self.id is not None else ""
        return f"{id_str}{self.title} by {self.author} ({self.page_count} pages) [{status}]"


class DVD(MediaItem):
    """Represents a DVD disc with runtime duration and handling instructions."""

    def __init__(self, title: str, author: str, duration: Any, is_available: bool = True):
        """Initialize a DVD instance including its runtime duration (int minutes or str)."""
        super().__init__(title, author, is_available)
        self.duration: Any = duration

    def checkout(self) -> str:
        """Check out the DVD and return handling instructions.

        Raises:
            ItemStateError: If the DVD is already checked out.
        """
        super().checkout()
        return "Handle with care: Do not scratch the disc. Successful checkout"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the DVD to a dictionary with type 'dvd' and duration."""
        data = super().to_dict()
        data["type"] = "dvd"
        data["duration"] = self.duration
        return data

    def __str__(self) -> str:
        """Return formatted string containing duration."""
        status = "Available" if self.is_available else "Checked Out"
        id_str = f"#{self.id} " if self.id is not None else ""
        return f"{id_str}{self.title} by {self.author} ({self.duration}) [{status}]"


class LibraryCollection:
    """Manages an inventory of MediaItem instances with CRUD capabilities."""

    def __init__(self):
        """Initialize an empty collection with sequential auto-incrementing ID counter."""
        self.items: List[MediaItem] = []
        self._next_id: int = 1

    def add_item(self, item: MediaItem) -> int:
        """Assign a unique auto-incrementing ID to the item, add it, and return the ID.

        IDs are never reused, even if items are deleted.
        """
        item.id = self._next_id
        self._next_id += 1
        self.items.append(item)
        return item.id

    def get_item(self, item_id: int) -> MediaItem:
        """Retrieve an item by its ID.

        Raises:
            ItemNotFoundError: If no item exists with the specified ID.
        """
        for item in self.items:
            if item.id == item_id:
                return item
        raise ItemNotFoundError(f"Item with id {item_id} not found.")

    def list_items(
        self, available: Optional[bool] = None, item_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return a list of item dictionaries (to_dict()), with optional filters.

        Args:
            available: Filter by availability (True, False, or None for all).
            item_type: Filter by media type ('book', 'dvd', 'media_item', or None for all).
        """
        result = []
        if isinstance(available, str):
            available = available.lower() == "true"

        for item in self.items:
            item_dict = item.to_dict()

            if available is not None and item.is_available != available:
                continue

            if item_type is not None:
                if str(item_dict.get("type", "")).lower() != item_type.lower():
                    continue

            result.append(item_dict)

        return result

    def update_item(self, item_id: int, **fields) -> MediaItem:
        """Update editable fields of an existing item.

        Editable fields: title, author, page_count, duration.

        Raises:
            ItemNotFoundError: If item does not exist.
            ValueError: If attempting to change restricted fields (id, type, is_available)
                        or unsupported attributes.
        """
        item = self.get_item(item_id)

        restricted_fields = {"id", "type", "is_available"}
        editable_fields = {"title", "author", "page_count", "duration"}

        for key, value in fields.items():
            if key in restricted_fields:
                raise ValueError(f"Changing '{key}' this way is not allowed.")
            if key not in editable_fields:
                raise ValueError(f"Field '{key}' is not editable.")
            if hasattr(item, key):
                setattr(item, key, value)
            else:
                raise ValueError(
                    f"Field '{key}' is not applicable to item type '{item.to_dict().get('type')}'."
                )

        return item

    def remove_item(self, item_id: int) -> MediaItem:
        """Remove an item from the collection.

        Raises:
            ItemNotFoundError: If item does not exist.
            ItemStateError: If the item is currently checked out.
        """
        item = self.get_item(item_id)
        if not item.is_available:
            raise ItemStateError(f"Cannot remove checked-out item #{item_id}.")
        self.items.remove(item)
        return item

    def list_available(self) -> List[str]:
        """Return a list of titles for all available items."""
        return [item.title for item in self.items if item.is_available]


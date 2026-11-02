"""Library Management System - Voice-Activated REST API Server.

EE 471 Mini Project #2.
Upgrades Week 4 Library App into a Voice-activated Library App using Azure Speech Services
(Speech-to-Text with SpeechRecognizer & Text-to-Speech with SpeechSynthesizer).
Exposes all standard CRUD endpoints + voice command processing endpoint.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from flask import Flask, jsonify, render_template, request

from custom_classes import (
    Book,
    DVD,
    ItemNotFoundError,
    ItemStateError,
    LibraryCollection,
    MediaItem,
)
from voice_parser import parse_voice_command
from voice_service import synthesize_speech_to_file, transcribe_audio_file

# Directory Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR = BASE_DIR / "templates"

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static"
)


# ---------------------------------------------------------------------------
# Collection Instance & Initial Seeding (Matching Week 4 Figma specifications)
# ---------------------------------------------------------------------------
def create_initial_library() -> LibraryCollection:
    """Instantiate and seed the library collection with initial Book and DVD items."""
    lib = LibraryCollection()
    lib.add_item(Book(title="The Great Gatsby", author="F. Scott Fitzgerald", page_count=180))
    lib.add_item(DVD(title="Inception", author="Christopher Nolan", duration=148))
    lib.add_item(Book(title="1984", author="George Orwell", page_count=328))
    lib.add_item(DVD(title="Arrival", author="Denis Villeneuve", duration=116))
    return lib


library = create_initial_library()


# ---------------------------------------------------------------------------
# Helper function for consistent error responses
# ---------------------------------------------------------------------------
def error_response(message: str, status_code: int):
    """Return JSON error response adhering strictly to assignment schema."""
    return jsonify({"error": message}), status_code


# ---------------------------------------------------------------------------
# Web UI Entry Point
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    """Serve the voice-activated library management frontend."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Standard Week 4 REST API Endpoints (Preserved 100%)
# ---------------------------------------------------------------------------

@app.route("/api/items", methods=["POST"])
def create_item():
    """Create a new Book or DVD item.

    Expected JSON body:
        title (str): Title of the item
        author (str): Author / Director name
        type (str): 'book' or 'dvd'
        page_count (int, if book): Number of pages
        duration (int/str, if dvd): Duration in minutes

    Returns:
        201: New item JSON representation
        400: Bad Request if validation fails
    """
    if not request.is_json:
        return error_response("Request body must be JSON.", 400)

    data: Dict[str, Any] = request.get_json() or {}

    title = data.get("title")
    author = data.get("author")
    item_type = str(data.get("type", "")).strip().lower()

    if not title or not isinstance(title, str) or not title.strip():
        return error_response("Field 'title' is required and must be non-empty.", 400)

    if not author or not isinstance(author, str) or not author.strip():
        return error_response("Field 'author' is required and must be non-empty.", 400)

    title = title.strip()
    author = author.strip()

    if item_type == "book":
        page_count = data.get("page_count")
        if page_count is None:
            return error_response("Field 'page_count' is required for Book.", 400)
        try:
            page_count_int = int(page_count)
            if page_count_int <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return error_response("Field 'page_count' must be a positive integer.", 400)

        new_item = Book(title=title, author=author, page_count=page_count_int)

    elif item_type == "dvd":
        duration = data.get("duration")
        if duration is None:
            return error_response("Field 'duration' is required for DVD.", 400)
        try:
            duration_val = int(duration)
            if duration_val <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            duration_val = duration

        new_item = DVD(title=title, author=author, duration=duration_val)

    else:
        return error_response("Invalid 'type'. Must be 'book' or 'dvd'.", 400)

    library.add_item(new_item)
    return jsonify(new_item.to_dict()), 201


@app.route("/api/items", methods=["GET"])
def list_items():
    """List collection items with optional query filters.

    Query parameters:
        available: 'true' or 'false'
        type: 'book' or 'dvd'

    Returns:
        200: List of items matching filters
        400: Bad filter query parameter
    """
    available_param = request.args.get("available")
    type_param = request.args.get("type")

    available_filter = None
    if available_param is not None:
        avail_lower = available_param.strip().lower()
        if avail_lower == "true":
            available_filter = True
        elif avail_lower == "false":
            available_filter = False
        else:
            return error_response("Invalid 'available' filter. Must be 'true' or 'false'.", 400)

    type_filter = None
    if type_param is not None:
        type_lower = type_param.strip().lower()
        if type_lower not in ["book", "dvd", "media_item"]:
            return error_response("Invalid 'type' filter. Must be 'book' or 'dvd'.", 400)
        type_filter = type_lower

    items = library.list_items(available=available_filter, item_type=type_filter)
    return jsonify(items), 200


@app.route("/api/items/<int:item_id>", methods=["GET"])
def get_item(item_id: int):
    """Retrieve details for a single item.

    Returns:
        200: Item JSON representation
        404: Not Found if item does not exist
    """
    try:
        item = library.get_item(item_id)
        return jsonify(item.to_dict()), 200
    except ItemNotFoundError as e:
        return error_response(str(e), 404)


@app.route("/api/items/<int:item_id>", methods=["PUT"])
def replace_item(item_id: int):
    """Replace all editable fields of an item.

    Returns:
        200: Updated item JSON
        400: Missing fields or invalid values
        404: Item not found
    """
    if not request.is_json:
        return error_response("Request body must be JSON.", 400)

    try:
        item = library.get_item(item_id)
    except ItemNotFoundError as e:
        return error_response(str(e), 404)

    data: Dict[str, Any] = request.get_json() or {}
    title = data.get("title")
    author = data.get("author")

    if not title or not author:
        return error_response("Fields 'title' and 'author' are required.", 400)

    try:
        if isinstance(item, Book):
            page_count = data.get("page_count")
            if page_count is None:
                return error_response("Field 'page_count' is required for Book.", 400)
            try:
                page_count_int = int(page_count)
                if page_count_int <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return error_response("Field 'page_count' must be a positive integer.", 400)

            library.update_item(
                item_id, title=title.strip(), author=author.strip(), page_count=page_count_int
            )

        elif isinstance(item, DVD):
            duration = data.get("duration")
            if duration is None:
                return error_response("Field 'duration' is required for DVD.", 400)
            try:
                duration_val = int(duration)
                if duration_val <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                duration_val = duration

            library.update_item(
                item_id, title=title.strip(), author=author.strip(), duration=duration_val
            )

        return jsonify(item.to_dict()), 200

    except ValueError as e:
        return error_response(str(e), 400)


@app.route("/api/items/<int:item_id>", methods=["PATCH"])
def update_item_partial(item_id: int):
    """Partially update editable fields of an item.

    Returns:
        200: Updated item JSON
        400: Invalid fields or attempts to modify restricted attributes
        404: Item not found
    """
    if not request.is_json:
        return error_response("Request body must be JSON.", 400)

    data: Dict[str, Any] = request.get_json() or {}
    if not data:
        return error_response("No update fields provided.", 400)

    if "page_count" in data:
        try:
            page_count_int = int(data["page_count"])
            if page_count_int <= 0:
                raise ValueError()
            data["page_count"] = page_count_int
        except (ValueError, TypeError):
            return error_response("Field 'page_count' must be a positive integer.", 400)

    if "duration" in data:
        try:
            duration_val = int(data["duration"])
            if duration_val <= 0:
                raise ValueError()
            data["duration"] = duration_val
        except (ValueError, TypeError):
            pass

    try:
        updated_item = library.update_item(item_id, **data)
        return jsonify(updated_item.to_dict()), 200
    except ItemNotFoundError as e:
        return error_response(str(e), 404)
    except ValueError as e:
        return error_response(str(e), 400)


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id: int):
    """Remove an item from the library.

    Returns:
        204: Successfully deleted (no content)
        404: Item not found
        409: Item is currently checked out
    """
    try:
        library.remove_item(item_id)
        return ("", 204)
    except ItemNotFoundError as e:
        return error_response(str(e), 404)
    except ItemStateError as e:
        return error_response(str(e), 409)


@app.route("/api/items/<int:item_id>/checkout", methods=["POST"])
def checkout_item(item_id: int):
    """Check out an item from the library.

    Returns:
        200: Successfully checked out
        404: Item not found
        409: Item is already checked out
    """
    try:
        item = library.get_item(item_id)
        message = item.checkout()
        return jsonify({"message": message, "item": item.to_dict()}), 200
    except ItemNotFoundError as e:
        return error_response(str(e), 404)
    except ItemStateError as e:
        return error_response(str(e), 409)


@app.route("/api/items/<int:item_id>/return", methods=["POST"])
def return_item(item_id: int):
    """Return a checked-out item to the library.

    Returns:
        200: Successfully returned
        404: Item not found
        409: Item is not currently checked out
    """
    try:
        item = library.get_item(item_id)
        message = item.return_item()
        return jsonify({"message": message, "item": item.to_dict()}), 200
    except ItemNotFoundError as e:
        return error_response(str(e), 404)
    except ItemStateError as e:
        return error_response(str(e), 409)


# ---------------------------------------------------------------------------
# Voice Command Processing (Endpoint POST /api/voice-command)
# ---------------------------------------------------------------------------
@app.route("/api/voice-command", methods=["POST"])
def process_voice_command():
    """Handle spoken audio payloads or text voice commands, execute parsed action,

    synthesize Librarian speech response, and return full transaction metadata.
    """
    recognized_text = ""
    temp_filepath = None

    # 1. Capture payload (Audio file upload OR JSON text simulation)
    if "audio" in request.files or "file" in request.files:
        audio_file = request.files.get("audio") or request.files.get("file")
        if not audio_file or not audio_file.filename:
            return error_response("Empty audio file received.", 400)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=UPLOAD_DIR) as tf:
            temp_filepath = tf.name
            audio_file.save(temp_filepath)

        try:
            recognized_text = transcribe_audio_file(temp_filepath)
        except ValueError as ve:
            return error_response(str(ve), 400)
        except RuntimeError as re:
            return error_response(f"Speech-to-Text error: {str(re)}", 500)
        finally:
            if temp_filepath and os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except OSError:
                    pass

    elif request.is_json:
        data = request.get_json() or {}
        recognized_text = data.get("text", "").strip()
        if not recognized_text:
            return error_response("Field 'text' is required when sending JSON to /api/voice-command.", 400)

    else:
        return error_response("Expected audio payload in form-data or JSON with 'text'.", 400)

    # 2. Parse voice command into structured intent & parameters
    cmd = parse_voice_command(recognized_text)

    action_success = False
    action_type = "unknown"
    spoken_response = ""
    response_data: Dict[str, Any] = {}

    if not cmd:
        spoken_response = "Sorry, I could not understand that command. Please try saying: create item, check out item, return item, or show available books."
        action_success = False
    else:
        action_type = cmd.get("action", "unknown")

        # -------------------------------------------------------------
        # A. CREATE ITEM (POST /api/items)
        # -------------------------------------------------------------
        if action_type == "create":
            item_type = cmd.get("type", "book")
            title = cmd.get("title", "").strip()
            author = cmd.get("author", "").strip()

            if item_type == "book":
                page_count = cmd.get("page_count", 1)
                new_item = Book(title=title, author=author, page_count=page_count)
            else:
                duration = cmd.get("duration", 60)
                new_item = DVD(title=title, author=author, duration=duration)

            library.add_item(new_item)
            action_success = True
            spoken_response = f"Successfully created {item_type} '{title}' with ID {new_item.id}."
            response_data = {
                "created_item": new_item.to_dict(),
                "items": library.list_items()
            }

        # -------------------------------------------------------------
        # B. CHECKOUT ITEM (POST /api/items/<id>/checkout)
        # -------------------------------------------------------------
        elif action_type == "checkout":
            item_id = cmd.get("item_id")
            try:
                item = library.get_item(item_id)
                item.checkout()
                action_success = True
                spoken_response = f"Item {item_id}, '{item.title}', has been checked out."
                response_data = {
                    "item": item.to_dict(),
                    "items": library.list_items()
                }
            except ItemNotFoundError:
                action_success = False
                spoken_response = f"Sorry, item {item_id} could not be found."
                response_data = {"error": f"Item with id {item_id} not found."}
            except ItemStateError:
                action_success = False
                spoken_response = f"Sorry, item {item_id} is already checked out."
                response_data = {"error": "Item is already checked out"}

        # -------------------------------------------------------------
        # C. RETURN ITEM (POST /api/items/<id>/return)
        # -------------------------------------------------------------
        elif action_type == "return":
            item_id = cmd.get("item_id")
            try:
                item = library.get_item(item_id)
                item.return_item()
                action_success = True
                spoken_response = f"Item {item_id}, '{item.title}', has been returned."
                response_data = {
                    "item": item.to_dict(),
                    "items": library.list_items()
                }
            except ItemNotFoundError:
                action_success = False
                spoken_response = f"Sorry, item {item_id} could not be found."
                response_data = {"error": f"Item with id {item_id} not found."}
            except ItemStateError:
                action_success = False
                spoken_response = f"Sorry, item {item_id} is not checked out."
                response_data = {"error": "Item is not checked out"}

        # -------------------------------------------------------------
        # D. DELETE ITEM (DELETE /api/items/<id>)
        # -------------------------------------------------------------
        elif action_type == "delete":
            item_id = cmd.get("item_id")
            try:
                library.remove_item(item_id)
                action_success = True
                spoken_response = f"Successfully deleted item {item_id}."
                response_data = {
                    "deleted_id": item_id,
                    "items": library.list_items()
                }
            except (ItemNotFoundError, ItemStateError) as e:
                action_success = False
                spoken_response = f"Could not delete item {item_id}. It may be checked out or doesn't exist."
                response_data = {"error": str(e)}

        # -------------------------------------------------------------
        # E. LIST / FILTER ITEMS (GET /api/items)
        # -------------------------------------------------------------
        elif action_type == "list":
            avail = cmd.get("available")
            m_type = cmd.get("type")
            filtered_items = library.list_items(available=avail, item_type=m_type)
            action_success = True

            if avail is True and m_type == "book":
                spoken_response = "Here are the available books in our catalog."
            elif avail is True and m_type == "dvd":
                spoken_response = "Here are the available DVDs in our catalog."
            elif avail is True:
                spoken_response = "Here are the available items in our catalog."
            elif m_type == "book":
                spoken_response = "Here are the books in our catalog."
            elif m_type == "dvd":
                spoken_response = "Here are the DVDs in our catalog."
            else:
                spoken_response = "Here are all items in our catalog."

            response_data = {
                "items": filtered_items,
                "filter": {"available": avail, "type": m_type}
            }

    # 3. Synthesize spoken librarian response with Azure TTS
    audio_url = None
    try:
        audio_url = synthesize_speech_to_file(spoken_response, filename="librarian_reply.wav")
    except Exception as tts_err:
        print(f"[Azure TTS Error] {tts_err}")

    return jsonify({
        "recognized_text": recognized_text,
        "action_success": action_success,
        "action": action_type,
        "spoken_response": spoken_response,
        "audio_url": audio_url,
        "data": response_data
    }), 200


# ---------------------------------------------------------------------------
# Server Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)


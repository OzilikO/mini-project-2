"""Voice Command Parser Module.

EE 471 Mini Project #2.
Parses natural English spoken commands transcribed from Azure Speech Services into
structured library actions and parameters matching the Library REST API.
"""

import re
from typing import Any, Dict, Optional

# Number word dictionary for converting spoken numbers to digits
WORD_TO_NUM: Dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "to": 2, "too": 2, "three": 3,
    "four": 4, "for": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ate": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "hundred": 100
}


def extract_number(val: Any) -> Optional[int]:
    """Extract an integer from a string or number, supporting digits and English words."""
    if val is None:
        return None
    if isinstance(val, int):
        return val

    val_str = str(val).strip().lower()

    # Direct digit match
    match = re.search(r"\d+", val_str)
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            pass

    # Word match
    tokens = re.findall(r"[a-z]+", val_str)
    total = 0
    found_any = False
    for token in tokens:
        if token in WORD_TO_NUM:
            found_any = True
            n = WORD_TO_NUM[token]
            if n == 100 and total > 0:
                total *= 100
            else:
                total += n

    if found_any:
        return total

    return None


def parse_voice_command(raw_text: str) -> Optional[Dict[str, Any]]:
    """Parse transcribed voice text into a structured library command.

    Supported Commands:
        1. Create:
           "Create item, type book, title The Catcher in the Rye, author J.D. Salinger, pages 220"
           "Create item, type dvd, title Inception, director Christopher Nolan, minutes 148"
        2. Checkout:
           "Check out item 3" / "Checkout item 3"
        3. Return:
           "Return item 3"
        4. Delete:
           "Delete item 3" / "Remove item 3"
        5. List / Filter:
           "Show available books" / "List DVDs" / "Show all items"

    Returns:
        Dict containing action and parsed parameters, or None if unparseable.
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    clean = raw_text.strip().rstrip(".?!")
    clean_lower = clean.lower()

    # -------------------------------------------------------------
    # 1. CHECKOUT COMMAND
    # -------------------------------------------------------------
    # Example: "Check out item 3", "Checkout item 3", "Check out 3", "Borrow item 3"
    m_checkout = re.search(
        r"\b(?:check\s*out|borrow)\b(?:\s+(?:item|id|number))?\s+([a-zA-Z0-9]+)",
        clean,
        re.I
    )
    if m_checkout:
        item_id = extract_number(m_checkout.group(1))
        if item_id is not None:
            return {
                "action": "checkout",
                "item_id": item_id,
                "raw_text": raw_text
            }

    # -------------------------------------------------------------
    # 2. RETURN COMMAND
    # -------------------------------------------------------------
    # Example: "Return item 3", "Return 3", "Bring back item 3"
    m_return = re.search(
        r"\b(?:return|give\s*back|bring\s*back)\b(?:\s+(?:item|id|number))?\s+([a-zA-Z0-9]+)",
        clean,
        re.I
    )
    if m_return:
        item_id = extract_number(m_return.group(1))
        if item_id is not None:
            return {
                "action": "return",
                "item_id": item_id,
                "raw_text": raw_text
            }

    # -------------------------------------------------------------
    # 3. DELETE COMMAND
    # -------------------------------------------------------------
    # Example: "Delete item 3", "Remove item 3", "Delete 3"
    m_delete = re.search(
        r"\b(?:delete|remove)\b(?:\s+(?:item|id|number))?\s+([a-zA-Z0-9]+)",
        clean,
        re.I
    )
    if m_delete:
        item_id = extract_number(m_delete.group(1))
        if item_id is not None:
            return {
                "action": "delete",
                "item_id": item_id,
                "raw_text": raw_text
            }

    # -------------------------------------------------------------
    # 4. CREATE COMMAND
    # -------------------------------------------------------------
    # Must check create before list in case someone says "Create item..."
    if re.search(r"\b(?:create|add|insert|new)\b", clean_lower):
        # Determine media type (default to book if unspecified)
        item_type = "book"
        if re.search(r"\bdvd\b", clean_lower):
            item_type = "dvd"
        elif re.search(r"\bbook\b", clean_lower):
            item_type = "book"

        # Try structured multi-field regex first
        # Pattern: title <title> author/director <author> pages/minutes/duration <number>
        structured_match = re.search(
            r"title\s+[:\-]?\s*(.+?)[,;]?\s+(?:author|director)\s+[:\-]?\s*(.+?)[,;]?\s+(?:pages?|minutes?|duration|length)\s+[:\-]?\s*([a-zA-Z0-9]+)",
            clean,
            re.I
        )

        title = None
        author = None
        metric = None

        if structured_match:
            title = structured_match.group(1).strip(" ,;'\"")
            author = structured_match.group(2).strip(" ,;'\"")
            metric = extract_number(structured_match.group(3))
        else:
            # Fallback regex extraction per field
            t_match = re.search(
                r"title\s+[:\-]?\s*(.+?)(?:[,;]|\s+author|\s+director|\s+pages|\s+minutes|\s+duration|$)",
                clean,
                re.I
            )
            a_match = re.search(
                r"(?:author|director)\s+[:\-]?\s*(.+?)(?:[,;]|\s+pages|\s+minutes|\s+duration|\s+title|$)",
                clean,
                re.I
            )
            p_match = re.search(
                r"(?:pages?|minutes?|duration|length)\s+[:\-]?\s*([a-zA-Z0-9]+)",
                clean,
                re.I
            )

            if t_match:
                title = t_match.group(1).strip(" ,;'\"")
            if a_match:
                author = a_match.group(1).strip(" ,;'\"")
            if p_match:
                metric = extract_number(p_match.group(1))

        if title and author and metric is not None:
            cmd = {
                "action": "create",
                "type": item_type,
                "title": title,
                "author": author,
                "raw_text": raw_text
            }
            if item_type == "book":
                cmd["page_count"] = metric
            else:
                cmd["duration"] = metric
            return cmd

    # -------------------------------------------------------------
    # 5. LIST / FILTER COMMAND
    # -------------------------------------------------------------
    # Example: "Show available books", "list DVDs", "show all items", "show available items"
    if re.search(r"\b(?:show|list|get|display|find|filter)\b", clean_lower):
        available = True if "available" in clean_lower else None
        item_type = None
        if re.search(r"\bbooks?\b", clean_lower):
            item_type = "book"
        elif re.search(r"\b(?:dvds?|movies?)\b", clean_lower):
            item_type = "dvd"

        is_all = bool(re.search(r"\b(?:all|catalog|items?|everything)\b", clean_lower))

        if item_type or available is not None or is_all:
            return {
                "action": "list",
                "available": available,
                "type": item_type,
                "raw_text": raw_text
            }

    return None


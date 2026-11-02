"""Automated Test Suite for Voice-Activated Library Management System.

EE 471 Mini Project #2.
Tests all REST endpoints and voice command interactions.
"""

import unittest
from app import app, library, create_initial_library


class VoiceLibraryTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        # Reset library collection with clean seed items
        global library
        import app as app_module
        app_module.library = create_initial_library()

    # -------------------------------------------------------------
    # 1. Standard REST Endpoints
    # -------------------------------------------------------------
    def test_get_all_items(self):
        res = self.client.get("/api/items")
        self.assertEqual(res.status_code, 200)
        items = res.get_json()
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 4)

    def test_filter_items(self):
        # Filter available=true
        res = self.client.get("/api/items?available=true")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()), 4)

        # Filter type=book
        res = self.client.get("/api/items?type=book")
        self.assertEqual(res.status_code, 200)
        items = res.get_json()
        self.assertEqual(len(items), 2)
        self.assertTrue(all(it["type"] == "book" for it in items))

    def test_create_item_rest(self):
        payload = {
            "title": "Brave New World",
            "author": "Aldous Huxley",
            "type": "book",
            "page_count": 268
        }
        res = self.client.post("/api/items", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["title"], "Brave New World")
        self.assertEqual(data["id"], 5)

    def test_create_item_bad_request(self):
        # Missing title
        res = self.client.post("/api/items", json={"author": "Nobody", "type": "book"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.get_json())

    def test_checkout_and_return_rest(self):
        # Checkout item 1
        res = self.client.post("/api/items/1/checkout")
        self.assertEqual(res.status_code, 200)

        # Checkout again -> 409
        res = self.client.post("/api/items/1/checkout")
        self.assertEqual(res.status_code, 409)
        self.assertIn("error", res.get_json())

        # Cannot delete checked out item -> 409
        res = self.client.delete("/api/items/1")
        self.assertEqual(res.status_code, 409)

        # Return item 1
        res = self.client.post("/api/items/1/return")
        self.assertEqual(res.status_code, 200)

        # Return again -> 409
        res = self.client.post("/api/items/1/return")
        self.assertEqual(res.status_code, 409)

    # -------------------------------------------------------------
    # 2. Voice Command Endpoint Tests
    # -------------------------------------------------------------
    def test_voice_create_book(self):
        res = self.client.post("/api/voice-command", json={
            "text": "Create item, type book, title The Catcher in the Rye, author J.D. Salinger, pages 220"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["action_success"])
        self.assertIn("Successfully created book 'The Catcher in the Rye' with ID", data["spoken_response"])
        self.assertIsNotNone(data["audio_url"])

    def test_voice_checkout_success_and_conflict(self):
        # 1st checkout -> Success
        res = self.client.post("/api/voice-command", json={"text": "Check out item 3"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["action_success"])
        self.assertEqual(data["spoken_response"], "Item 3, '1984', has been checked out.")

        # 2nd checkout -> Already checked out
        res = self.client.post("/api/voice-command", json={"text": "Check out item 3"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["action_success"])
        self.assertEqual(data["spoken_response"], "Sorry, item 3 is already checked out.")

    def test_voice_return_success_and_conflict(self):
        # Checkout item 2
        self.client.post("/api/items/2/checkout")

        # Return item 2 via voice
        res = self.client.post("/api/voice-command", json={"text": "Return item 2"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["action_success"])
        self.assertEqual(data["spoken_response"], "Item 2, 'Inception', has been returned.")

        # Return item 2 again -> not checked out
        res = self.client.post("/api/voice-command", json={"text": "Return item 2"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["action_success"])
        self.assertEqual(data["spoken_response"], "Sorry, item 2 is not checked out.")

    def test_voice_delete(self):
        res = self.client.post("/api/voice-command", json={"text": "Delete item 4"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["action_success"])
        self.assertEqual(data["spoken_response"], "Successfully deleted item 4.")

    def test_voice_list_filters(self):
        res = self.client.post("/api/voice-command", json={"text": "Show available books"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["action_success"])
        self.assertEqual(data["spoken_response"], "Here are the available books in our catalog.")
        self.assertEqual(len(data["data"]["items"]), 2)


if __name__ == "__main__":
    unittest.main()

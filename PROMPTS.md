# EE 471 Mini Project #2 - Vibe Coding Transcripts & Development Log

## Project Title: Voice-Activated Library Management System
**Course:** EE 471 Modern Software Development Practices and Technologies  
**Institution:** Izmir Institute of Technology - Electrical and Electronics Eng. Dep.  
**Repository:** [https://github.com/OzilikO/mini-project-2.git](https://github.com/OzilikO/mini-project-2.git)

---

## 1. Project Overview & Architecture

Mini Project #2 upgrades the Week 4 Library Management App into a fully voice-activated application using **Azure Speech Services** (Azure Cognitive Services Speech SDK). The application allows users to speak commands naturally into the microphone to perform CRUD, Checkout, Return, and List operations on library catalog items (Books and DVDs), and provides real-time spoken feedback ("Librarian Response") powered by Azure Neural Voice (`en-US-JennyNeural`).

```
+---------------------------------------------------------------------------------+
|                                Frontend (Browser)                                |
|  - HTML5 AudioContext & ScriptProcessor (WavAudioRecorder: 16-bit PCM WAV)      |
|  - Glowing circular Microphone UI & Live Voice Action Panel                     |
|  - Floating bottom-center Librarian Response Banner                             |
|  - Dynamic Card state updates & Modal Form Pop-verification                     |
+---------------------------------------------------------------------------------+
                                      |
                           HTTP Multipart / JSON
                                      v
+---------------------------------------------------------------------------------+
|                               Backend (Flask App)                               |
|                                                                                 |
|  [ Azure SpeechRecognizer ] <--- Transcribe microphoned WAV audio payload       |
|            |                                                                    |
|            v                                                                    |
|  [ voice_parser.py ]       <--- Regex & Intent extraction (create, checkout...) |
|            |                                                                    |
|            v                                                                    |
|  [ custom_classes.py ]     <--- LibraryCollection CRUD & State Validation       |
|            |                                                                    |
|            v                                                                    |
|  [ voice_service.py ]      <--- Azure SpeechSynthesizer (en-US-JennyNeural)     |
|            |                                                                    |
|            v                                                                    |
|  Returns: JSON payload + /static/librarian_reply.wav?t=...                      |
+---------------------------------------------------------------------------------+
```

---

## 2. Voice Command Syntax & Endpoint Mapping

| User Spoken Voice Input | Extracted Action | Backend API Route | Librarian Spoken Audio Response |
| :--- | :--- | :--- | :--- |
| `"Create item, type book, title The Catcher in the Rye, author J.D. Salinger, pages 220"` | Create Book | `POST /api/items` | *"Successfully created book 'The Catcher in the Rye' with ID 3."* |
| `"Create item, type dvd, title Inception, director Christopher Nolan, minutes 148"` | Create DVD | `POST /api/items` | *"Successfully created dvd 'Inception' with ID 4."* |
| `"Check out item 3"` | Checkout | `POST /api/items/3/checkout` | *"Item 3, '1984', has been checked out."* |
| `"Check out item 3"` *(already out)* | Conflict (409) | `POST /api/items/3/checkout` | *"Sorry, item 3 is already checked out."* |
| `"Return item 3"` | Return | `POST /api/items/3/return` | *"Item 3, '1984', has been returned."* |
| `"Return item 3"` *(not out)* | Conflict (409) | `POST /api/items/3/return` | *"Sorry, item 3 is not checked out."* |
| `"Delete item 1"` | Delete | `DELETE /api/items/1` | *"Successfully deleted item 1."* |
| `"Show available books"` | Filter | `GET /api/items?available=true&type=book` | *"Here are the available books in our catalog."* |
| `"list DVDs"` | Filter | `GET /api/items?type=dvd` | *"Here are the DVDs in our catalog."* |
| `"show all items"` | Reset Filter | `GET /api/items` | *"Here are all items in our catalog."* |

---

## 3. Vibe Coding Prompt Transcripts

### Session Prompt 1: Initial Requirements & PDF Extraction
> **User Prompt:**  
> In accordance with the file at path `D:\EE\mini-project-2\Mini-Project-2.pdf`, please upgrade our Week 4 Library App into a "Voice-activated Library App" using Azure Speech Services (Speech-to-Text and Text-to-Speech) for Mini Project #2.  
> Our application must allow natural voice inputs to trigger/run any of the available CRUD, Checkout, and Return endpoints, and it must read back the outcome ("Librarian response") as speech at the end of each command.  
> Please analyze the original Week 4 core logic, frontend layouts, and add the following voice components without breaking any existing features:
> 1. Security & Environment Setup (`.env`, `load_dotenv`, `.gitignore`)
> 2. Voice Command Parsing & Backend Logic (`app.py`, `voice_parser.py`)
> 3. Text-to-Speech Synthesis (`voice_service.py` with `en-US-JennyNeural`)
> 4. Voice Command Endpoint (`POST /api/voice-command`)
> 5. Frontend Integration (`index.html`, `script.js`, `style.css`)

### Session Prompt 2: Azure Audio In-Browser Capture
> **Agent Implementation Decision:**  
> Standard browser `MediaRecorder` frequently emits compressed `audio/webm` or `audio/ogg`, which requires server-side `ffmpeg` transcoding before Azure's native 16-bit PCM WAV recognizer can parse it.  
> To eliminate external binary dependencies and provide 100% native compatibility, implemented `WavAudioRecorder` directly in JavaScript using `AudioContext` and `ScriptProcessorNode` to construct valid RIFF/WAVE 16-bit PCM audio buffers on the client side before POSTing to `/api/voice-command`.

### Session Prompt 3: Natural Language Regular Expression Pipeline
> **Agent Implementation Decision:**  
> Implemented multi-stage regex matching with spoken number-to-digit conversion (e.g., converting spoken "three" to integer `3`, "two" to `2`, etc.). Designed flexible delimiters for title, author/director, and pages/minutes to seamlessly accommodate commas, colons, or natural speech pauses.

### Session Prompt 4: Dynamic UI Feedback & Form Popping
> **Agent Implementation Decision:**  
> Requirement specifies: *"Pop/unpop the item forms if 'create' commands are visually processed so the user can verify the form fill/action directly."*  
> When a voice creation command succeeds, `popCreateVerification(item)` opens the modal dialog populated with title, author, media type, and page count/duration, and automatically closes it after 1.8 seconds while triggering a subtle highlight ripple on the newly appended catalog card.

---

## 4. Security & Environment Management

1. **Credentials Isolation:**
   - Keys (`SPEECH_KEY`, `SPEECH_REGION`) are stored in `.env`.
   - `.env` is explicitly declared in `.gitignore` to prevent leaking secrets to GitHub.
   - `.env.example` provides template configuration for graders and collaborators.
2. **Safe Loading:**
   - Handled via `python-dotenv` (`load_dotenv()`) across all entry points.
3. **Container Safety:**
   - `.dockerignore` excludes `.env`, `uploads/`, and temporary `.wav` files.

---

## 5. Verification & Testing

The test suite (`test_voice_library.py`) executes 10 comprehensive unit tests:
- `test_get_all_items`: Verifies 200 OK and initial seeding.
- `test_filter_items`: Verifies query parameters `?available=true` and `?type=book`.
- `test_create_item_rest`: Verifies standard REST POST item creation.
- `test_create_item_bad_request`: Verifies 400 Bad Request on invalid payloads.
- `test_checkout_and_return_rest`: Verifies 200 OK, 409 Conflict, and checkout/return states.
- `test_voice_create_book`: Tests voice parsing, catalog addition, and TTS reply.
- `test_voice_checkout_success_and_conflict`: Tests voice checkout and error handling (409).
- `test_voice_return_success_and_conflict`: Tests voice return and error handling (409).
- `test_voice_delete`: Tests voice delete endpoint.
- `test_voice_list_filters`: Tests voice catalog filtering.

Result:
```text
Ran 10 tests in 19.499s
OK
```

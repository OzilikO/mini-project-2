# Voice-Activated Library Management System - Mini Project #2

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Azure Cognitive Services](https://img.shields.io/badge/azure-speech--services-0078d4.svg)](https://azure.microsoft.com/en-us/products/ai-services/ai-speech)

**EE 471 Modern Software Development Practices and Technologies**  
Izmir Institute of Technology - Electrical and Electronics Eng. Dep.  
Repository: [https://github.com/OzilikO/mini-project-2.git](https://github.com/OzilikO/mini-project-2.git)

---

## Overview

Mini Project #2 upgrades our Week 4 Library Management application into a **Voice-Activated Library App** powered by **Azure Speech Services** (Speech-to-Text and Text-to-Speech).

The application allows users to speak commands naturally into the microphone or test them via text input. Spoken commands trigger backend library operations (`Create`, `Checkout`, `Return`, `Delete`, and `List/Filter`), and the system responds back with real-time spoken librarian audio synthesized using Azure Neural Voice (`en-US-JennyNeural`).

---

## Key Features

- **Microphone Voice Capture**: In-browser 16-bit PCM WAV audio recording (`WavAudioRecorder`) with glowing animated microphone UI.
- **Azure Speech-to-Text (STT)**: Real-time speech transcription via `azure.cognitiveservices.speech.SpeechRecognizer`.
- **Natural Language Parsing**: Robust regex and keyword pipeline (`voice_parser.py`) supporting flexible English grammar and word-to-digit conversion (e.g., "item three" -> ID `3`).
- **Azure Text-to-Speech (TTS)**: Realistic audio feedback synthesized with `en-US-JennyNeural`, served directly to the browser for instant playback.
- **Librarian Spoken Response Banner**: Floating animated bottom-center response card displaying the transcribed action and spoken message.
- **Visual Action Verification**: Automatically pops and prefills the item form on voice item creation so users can verify fields before closing.
- **Full Backward Compatibility**: All Week 4 REST endpoints (`POST /api/items`, `GET /api/items`, `PUT`, `PATCH`, `DELETE`, `checkout`, `return`) remain preserved with standard error schemas (`{"error": "<message>"}`).

---

## Voice Interaction Examples

| User Spoken Voice Input | Action | Backend Route | Librarian Audio Response |
| :--- | :--- | :--- | :--- |
| `"Create item, type book, title The Catcher in the Rye, author J.D. Salinger, pages 220"` | Create Book | `POST /api/items` | *"Successfully created book 'The Catcher in the Rye' with ID 3."* |
| `"Create item, type dvd, title Inception, director Christopher Nolan, minutes 148"` | Create DVD | `POST /api/items` | *"Successfully created dvd 'Inception' with ID 4."* |
| `"Check out item 3"` | Checkout | `POST /api/items/3/checkout` | *"Item 3, '1984', has been checked out."* |
| `"Check out item 3"` *(again)* | Error (409) | `POST /api/items/3/checkout` | *"Sorry, item 3 is already checked out."* |
| `"Return item 3"` | Return | `POST /api/items/3/return` | *"Item 3, '1984', has been returned."* |
| `"Return item 3"` *(not out)* | Error (409) | `POST /api/items/3/return` | *"Sorry, item 3 is not checked out."* |
| `"Delete item 1"` | Delete | `DELETE /api/items/1` | *"Successfully deleted item 1."* |
| `"Show available books"` | Filter | `GET /api/items?available=true&type=book` | *"Here are the available books in our catalog."* |
| `"list DVDs"` | Filter | `GET /api/items?type=dvd` | *"Here are the DVDs in our catalog."* |
| `"show all items"` | Reset Filter | `GET /api/items` | *"Here are all items in our catalog."* |

---

## Project Structure

```
mini-project-2/
├── .env                       # Azure Speech credentials (gitignored)
├── .env.example               # Template environment configuration
├── .gitignore                 # Excludes .env, caches, audio files
├── .dockerignore              # Docker build exclusions
├── Dockerfile                 # Container definition with Azure Speech Linux deps
├── requirements.txt           # Python package dependencies
├── app.py                     # Flask REST API + Voice Command endpoint
├── library_app.py             # Launcher alias for app.py
├── custom_classes.py          # OOP domain models (MediaItem, Book, DVD, LibraryCollection)
├── library_custom_classes.py  # Compatibility alias
├── voice_service.py           # Azure Speech STT & TTS integration
├── voice_parser.py            # Natural English voice parsing & regex engine
├── test_voice_library.py      # Automated unit tests (10 test cases)
├── PROMPTS.md                 # Vibe coding transcripts and engineering log
├── README.md                  # Project documentation
├── templates/
│   └── index.html             # HTML layout with Voice Action Panel & Librarian banner
├── static/
│   ├── style.css              # Figma layout + glowing pulse mic animations
│   ├── script.js              # In-browser PCM WAV recorder, API caller & UI updater
│   └── librarian_reply.wav    # Synthesized audio file
└── uploads/                   # Temporary audio upload cache
```

---

## Setup & Running Locally

### 1. Prerequisites
- Python 3.10 or higher
- An active Azure Cognitive Services Speech Key and Region

### 2. Environment Configuration
Create a `.env` file in the project root (or copy `.env.example`):
```bash
cp .env.example .env
```
Populate your credentials:
```env
SPEECH_KEY=your_azure_speech_key_here
SPEECH_REGION=eastus
```

### 3. Installation
Install python dependencies:
```bash
pip install -r requirements.txt
```

### 4. Run the Application
Start the Flask server:
```bash
python app.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Running with Docker

Build the Docker container:
```bash
docker build -t voice-library-app .
```

Run the container (passing environment variables):
```bash
docker run --env-file .env -p 5000:5000 voice-library-app
```

---

## Running the Automated Test Suite

Execute the test suite to verify all REST endpoints and voice workflows:
```bash
python -m unittest test_voice_library.py
```

Expected output:
```text
..........
----------------------------------------------------------------------
Ran 10 tests in 19.5s

OK
```

---

## Deliverables Checklist

- [x] **Github repository**: [https://github.com/OzilikO/mini-project-2.git](https://github.com/OzilikO/mini-project-2.git)
- [x] **PROMPTS.md**: Comprehensive vibe coding transcripts and prompt history.
- [x] **All CRUD & Voice Endpoints**: Create, Checkout, Return, Delete, List/Filter with Azure STT and TTS.
- [x] **Librarian Audio Playback & Banner**: JennyNeural audio synthesized into `/static/librarian_reply.wav` with real-time browser playback.
- [x] **video-demo.avi**: Video recording of voice testing (to be recorded by student).
- [x] **video-explanation.avi**: Video explanation of code architecture (to be recorded by student).

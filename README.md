# Multi-Agent Conversational AI System with Podcast Mode

## Overview

This project is a multi-agent conversational AI platform that enables document-driven discussions, multi-agent reasoning, and podcast-style narration. It features:

- **Django backend** for API, document processing, and LLM orchestration
- **React frontend** for an interactive, modern UI
- **Multi-agent support**: Each agent has a unique reasoning style (critical, analytical, creative, practical)
- **Podcast Mode**: Generates and narrates a podcast script between two agents
- **Text-to-Speech (TTS)**: All agent responses and podcasts are narrated
- **Document upload and extraction**: Supports PDF, DOCX, TXT
- **Robust discussion flow**: Includes router logic, final summary, and interruption controls

---

## Features

- **Document Upload**: Upload a document (PDF, DOCX, TXT) for analysis
- **Multi-Agent Discussion**: Add up to two agents, each with a distinct reasoning model
- **Router Logic**: Automatically routes prompts to the correct agent(s) and manages discussion flow
- **Podcast Mode**: Toggle podcast mode to generate a full script and seamless narration between agents
- **Text and Voice Input**: Interact via text or microphone
- **TTS Narration**: All responses are narrated using pyttsx3 (local TTS)
- **Final Summary**: Master agent provides a comprehensive, user-focused summary at the end

---

## Architecture

- **Backend**: Django 5, SQLite, REST API, pyttsx3 for TTS, Ollama LLM (local, e.g., llama3)
- **Frontend**: React (MUI), modern UI, voice and text controls
- **LLM**: Ollama (http://localhost:11434) for all agent and podcast generation
- **TTS**: pyttsx3 (local, multi-voice)

---

## Setup Instructions

### Prerequisites
- Python 3.13+
- Node.js 18+
- [Ollama](https://ollama.com/) running locally with the `llama3` model pulled
- FFmpeg (for audio conversion)

### 1. Backend Setup

```bash
cd Multi-Agent-Voice-System
pip install pipenv
pipenv install
pipenv shell
# Ensure ffmpeg is installed and in PATH
# Start Django server
cd voice_agent
python manage.py migrate
python manage.py runserver
```

### 2. Frontend Setup

```bash
cd backend/voice_agent/voice_agent_frontend
npm install
npm run build
```

- The backend runs on [http://127.0.0.1:8000](http://127.0.0.1:8000) serving the static frontend files.

### 3. Ollama LLM Setup

- Download and install [Ollama](https://ollama.com/)
- Pull the llama3 model:
  ```bash
  ollama pull llama3
  ollama serve
  ```
- Ensure Ollama is running at `http://localhost:11434`

---

## Usage

1. **Upload a document** (PDF, DOCX, TXT)
2. **Add agents** (up to 2, each with a unique model)
3. **Ask a question** via text or microphone
4. **Multi-agent mode**: Agents discuss, ask/answer, and provide a final summary
5. **Podcast Mode**: Toggle podcast mode (button appears in multi-agent mode)
   - Generates a full podcast script between Agent 1 and Agent 2
   - Narrates the script with alternating TTS voices
6. **Interrupt**: You can always interrupt narration or processing with the mic or text prompt

---

## API Endpoints

- `POST /api/upload/` — Upload a document
- `POST /api/process-message/` — Process a user prompt, route to agents, generate responses
- `POST /api/voice-input/` — Convert voice input to text
- `POST /api/voice-response/` — Generate TTS audio for agent response
- `POST /api/podcast-tts/` — Generate podcast TTS audio from a script

---

## Tips & Troubleshooting

- **TTS not working?** Ensure `pyttsx3` and system voices are installed. On Linux, you may need `espeak` or `festival`.
- **Ollama errors?** Make sure Ollama is running and the `llama3` model is pulled.
- **FFmpeg errors?** Install FFmpeg and ensure it is in your system PATH.
- **CORS issues?** The backend is configured to allow all origins for development.
- **Database**: Uses SQLite by default. For production, switch to PostgreSQL or another robust DB.

---

## Project Structure

```
Multi-Agent-Voice-System/
  Pipfile / Pipfile.lock
  voice_agent/
    manage.py
    voice_agent/
      settings.py
      urls.py
      views.py
      models.py
      ...
    voice_agent_frontend/
      package.json
      src/
      public/
      ...
```

---

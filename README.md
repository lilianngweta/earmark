# Earmark

Turns your Markdown build logs into fun, podcast-style audio episodes — narrated by AI (via the [ElevenLabs](https://elevenlabs.io) Text-to-Speech API) and playable right in the browser.

Drop in a file like `SUMMARY.md` and get back a "Build Log" episode: an intro, a chapter-by-chapter walkthrough of each section, and an outro — read aloud in a warm, conversational voice.

There are two ways to use it:
- **`audio_agent.py`** — a command-line agent that converts a single Markdown file to an MP3.
- **`app.py`** — a small Flask web app where you can upload `.md` files and play the resulting episodes in your browser.

## Requirements

- Python 3.9+
- An [ElevenLabs](https://elevenlabs.io) account and API key

## Setup

From the project directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Then set your ElevenLabs API key as an environment variable (needed for both the CLI agent and the web app):

```bash
export ELEVENLABS_API_KEY="sk-..."
```

## Option 1: Command-line agent

Convert a Markdown file straight to an MP3:

```bash
.venv/bin/python audio_agent.py SUMMARY.md -o narration.mp3
```

Preview the generated podcast script first, without calling the API or needing a key:

```bash
.venv/bin/python audio_agent.py SUMMARY.md --script-only
```

Useful flags:

| Flag | Purpose |
| --- | --- |
| `-o, --output` | Where to write the audio file (default: `narration.mp3`) |
| `--script-out` | Save the generated narration script to a text file |
| `--script-only` | Generate (and print/save) the script without calling ElevenLabs |
| `--voice-id` | Choose a different ElevenLabs voice |
| `--stability`, `--similarity-boost`, `--style` | Tune the voice's delivery (see `--help` for details) |

## Option 2: Web app

Start the server:

```bash
export ELEVENLABS_API_KEY="sk-..."
.venv/bin/python app.py
```

Then open **http://127.0.0.1:5050** in your browser. Drag a `.md` file into the upload area (or click to browse), hit **Generate episode**, and once it's ready you can play it right on the page. Every episode you generate is saved to an **Episode library** below so you can replay it later.

Generated audio files are stored in `generated/` and indexed in `episodes.json`.

## Project structure

```
audio_thinker/
├── audio_agent.py       # CLI agent: Markdown -> podcast script -> MP3
├── app.py               # Flask web app
├── templates/
│   └── index.html       # Upload page / player / episode library
├── static/
│   ├── css/style.css
│   └── js/app.js
├── generated/           # Generated MP3s land here
├── episodes.json        # Index of generated episodes (created at runtime)
└── requirements.txt
```

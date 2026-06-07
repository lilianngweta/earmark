#!/usr/bin/env python3
"""Earmark — a tiny web app that turns uploaded Markdown files into
playable, podcast-style audio episodes using the ElevenLabs TTS agent in
audio_agent.py.

Run with:
    export ELEVENLABS_API_KEY="sk-..."
    .venv/bin/python app.py
Then open http://127.0.0.1:5050 in a browser.
"""

import json
import os
import time
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from audio_agent import (
    DEFAULT_MODEL_ID,
    DEFAULT_VOICE_ID,
    build_narration,
    chunk_text,
    clean_inline_markdown,
    parse_markdown,
    synthesize_chunk,
)

BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated"
EPISODES_FILE = BASE_DIR / "episodes.json"
GENERATED_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = (".md", ".markdown", ".txt")
VOICE_SETTINGS = {
    "stability": 0.45,
    "similarity_boost": 0.75,
    "style": 0.35,
    "use_speaker_boost": True,
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # Markdown summaries are tiny; 2 MB is generous


def load_episodes():
    if EPISODES_FILE.exists():
        return json.loads(EPISODES_FILE.read_text(encoding="utf-8"))
    return []


def save_episodes(episodes):
    EPISODES_FILE.write_text(json.dumps(episodes, indent=2), encoding="utf-8")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/episodes")
def list_episodes():
    return jsonify(load_episodes())


@app.delete("/api/episodes/<episode_id>")
def delete_episode(episode_id):
    episodes = load_episodes()
    remaining = [episode for episode in episodes if episode["id"] != episode_id]
    if len(remaining) == len(episodes):
        abort(404)

    audio_path = GENERATED_DIR / f"{episode_id}.mp3"
    if audio_path.is_file():
        audio_path.unlink()

    save_episodes(remaining)
    return "", 204


@app.get("/audio/<path:filename>")
def serve_audio(filename):
    audio_path = GENERATED_DIR / filename
    if not audio_path.is_file():
        abort(404)
    return send_from_directory(GENERATED_DIR, filename)


@app.post("/api/generate")
def generate_episode():
    upload = request.files.get("markdown")
    if upload is None or not upload.filename:
        return jsonify(error="Please choose a Markdown (.md) file to upload."), 400
    if not upload.filename.lower().endswith(ALLOWED_EXTENSIONS):
        return jsonify(error="That doesn't look like a Markdown file — please upload a .md file."), 400

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        return jsonify(error="The server is missing ELEVENLABS_API_KEY — set it and restart the app."), 500

    raw_text = upload.read().decode("utf-8", errors="replace")
    title, intro_text, sections = parse_markdown(raw_text)
    if not title and not sections:
        return jsonify(error="Couldn't find any Markdown headings to narrate in that file."), 400

    script = build_narration(title, intro_text, sections)

    episode_id = uuid.uuid4().hex[:12]
    audio_path = GENERATED_DIR / f"{episode_id}.mp3"

    try:
        audio_bytes = bytearray()
        for chunk in chunk_text(script):
            audio_bytes.extend(
                synthesize_chunk(chunk, api_key, DEFAULT_VOICE_ID, DEFAULT_MODEL_ID, VOICE_SETTINGS)
            )
        audio_path.write_bytes(audio_bytes)
    except Exception as exc:
        return jsonify(error=f"Couldn't generate audio: {exc}"), 502

    episode = {
        "id": episode_id,
        "title": clean_inline_markdown(title) or upload.filename,
        "source_filename": upload.filename,
        "audio_url": f"/audio/{audio_path.name}",
        "script": script,
        "created_at": int(time.time()),
    }

    episodes = load_episodes()
    episodes.insert(0, episode)
    save_episodes(episodes)

    return jsonify(episode)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)

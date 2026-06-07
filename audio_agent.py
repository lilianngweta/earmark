#!/usr/bin/env python3
"""Turn a Markdown build summary into a fun, podcast-style audio narration.

The agent reads a Markdown file (e.g. SUMMARY.md), rewrites its sections into a
conversational "Build Log" podcast script — complete with an intro, chapter-by-
chapter walkthroughs, and an outro — and then sends that script to the
ElevenLabs Text-to-Speech API to render it as an MP3.

Usage:
    export ELEVENLABS_API_KEY="sk-..."
    python3 audio_agent.py SUMMARY.md -o narration.mp3

    # Preview the generated narration script without calling the API
    # (no API key required):
    python3 audio_agent.py SUMMARY.md --script-only
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" — warm, expressive narrator voice
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
MAX_CHUNK_CHARS = 2200  # keep individual TTS requests comfortably under API limits

NUMBER_WORDS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]

LEAD_INS = [
    "Let's start right at the beginning.",
    "Alright, onward —",
    "Here's where things start moving.",
    "Now, here's where it gets fun.",
    "Let's keep the momentum going.",
    "Onward to the next chapter.",
    "And from there,",
]

CONNECTORS = ["First,", "Next,", "Then,", "On top of that,", "And then,", "Finally,"]


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

def parse_markdown(raw_text):
    """Split a Markdown document into (h1_title, intro_text, [(h2_heading, body_lines)])."""
    title = ""
    intro_lines = []
    sections = []
    current_heading = None
    current_body = []
    seen_h1 = False

    for line in raw_text.splitlines():
        h1 = re.match(r"^#\s+(.*)", line)
        h2 = re.match(r"^##\s+(.*)", line)
        if h1 and not seen_h1:
            title = h1.group(1).strip()
            seen_h1 = True
            continue
        if h2:
            if current_heading is not None:
                sections.append((current_heading, current_body))
            current_heading = h2.group(1).strip()
            current_body = []
            continue
        if current_heading is None:
            intro_lines.append(line)
        else:
            current_body.append(line)

    if current_heading is not None:
        sections.append((current_heading, current_body))

    return title, "\n".join(intro_lines).strip(), sections


def clean_inline_markdown(text):
    """Strip Markdown syntax that would otherwise be read aloud verbatim."""
    # Drop parenthetical asides that contain a raw URL or shell command, e.g.
    # "(`https://example.com/page`)" or "(`open http://localhost:8743/x.html`)" —
    # these read poorly aloud and the surrounding sentence stays meaningful
    # without them, so we remove the whole aside rather than leave orphaned
    # punctuation behind once the URL itself is stripped.
    text = re.sub(r"\([^()]*https?://[^()]*\)\s*", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)  # raw HTML tags, e.g. <pre><code>
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def lower_first(text):
    return text[:1].lower() + text[1:] if text else text


def ensure_sentence(text):
    text = text.strip()
    if text and not text.endswith((".", "!", "?", ":")):
        text += "."
    return text


def is_bare_label(cleaned):
    """True for short, colon-terminated remnants like "Source paper:" — these are
    almost always "Label: <link>" lines whose link got stripped during cleaning."""
    return cleaned.endswith(":") and len(cleaned) < 40


def clean_prose_block(raw_text):
    """Clean a block of prose for narration: join line-wrapped paragraphs into
    single sentences, strip Markdown syntax, and drop link-only label remnants."""
    paragraphs, buffer = [], []
    for line in raw_text.splitlines():
        if line.strip():
            buffer.append(line.strip())
        else:
            if buffer:
                paragraphs.append(" ".join(buffer))
                buffer = []
    if buffer:
        paragraphs.append(" ".join(buffer))

    sentences = []
    for para in paragraphs:
        cleaned = clean_inline_markdown(para)
        if cleaned and not is_bare_label(cleaned):
            sentences.append(ensure_sentence(cleaned))
    return " ".join(sentences)


def section_body_to_sentences(body_lines):
    """Convert a section's raw lines into spoken sentences.

    Returns (sentences, had_code_block, had_prose). Fenced code blocks are
    dropped from narration (file trees and snippets don't read aloud well) but
    we note their presence so the script can call that out for laughs.
    """
    sentences = []
    bullet_buffer = []
    para_buffer = []
    had_code = False
    had_prose = False

    def flush_bullets():
        nonlocal had_prose
        for idx, raw in enumerate(bullet_buffer):
            cleaned = clean_inline_markdown(raw)
            if not cleaned:
                continue
            connector = CONNECTORS[idx % len(CONNECTORS)]
            sentences.append(ensure_sentence(f"{connector} {lower_first(cleaned)}"))
            had_prose = True
        bullet_buffer.clear()

    def flush_paragraph():
        nonlocal had_prose
        if not para_buffer:
            return
        cleaned = clean_inline_markdown(" ".join(para_buffer))
        para_buffer.clear()
        if cleaned and not is_bare_label(cleaned):
            sentences.append(ensure_sentence(cleaned))
            had_prose = True

    i, n = 0, len(body_lines)
    while i < n:
        line = body_lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_bullets()
            had_code = True
            i += 1
            while i < n and not body_lines[i].strip().startswith("```"):
                i += 1
            i += 1
            continue

        bullet_match = re.match(r"^(\s*)-\s+(.*)", line)
        if bullet_match:
            flush_paragraph()
            indent = len(bullet_match.group(1))
            buf = bullet_match.group(2).strip()
            i += 1
            # Fold any deeper-indented sub-bullets into the parent bullet's
            # sentence (joined with semicolons) so a heading like "index.html"
            # stays connected to the items it describes, instead of becoming a
            # string of disconnected one-word "sentences".
            while i < n:
                cont = body_lines[i]
                cont_stripped = cont.strip()
                if not cont_stripped:
                    break
                sub_match = re.match(r"^(\s*)-\s+(.*)", cont)
                if sub_match:
                    if len(sub_match.group(1)) > indent:
                        addition = sub_match.group(2).strip()
                        trimmed = buf.rstrip()
                        # A trailing colon ("...static assets:") already cues a
                        # list, so a plain space reads more naturally than
                        # piling on a redundant "...assets:; item one; item two".
                        # A trailing period gets dropped so consecutive items
                        # don't collide into an awkward "...citation.; Abstract".
                        if trimmed.endswith(":"):
                            buf = f"{trimmed} {addition}"
                        else:
                            buf = f"{trimmed.rstrip('.')}; {addition}"
                        i += 1
                        continue
                    break
                if cont_stripped.startswith(("#", "```")):
                    break
                buf += " " + cont_stripped
                i += 1
            bullet_buffer.append(buf)
            continue

        if not stripped:
            # Blank lines split prose into separate paragraphs/sentences, but
            # bullet groups in this Markdown are sometimes visually separated
            # by blank lines while still describing the same list (e.g. two
            # files, each followed by its own sub-bullets) — flushing here
            # would restart the "First, / Next, ..." connector mid-list, so we
            # let bullet_buffer keep accumulating until prose or EOF closes it.
            flush_paragraph()
            i += 1
            continue

        flush_bullets()
        para_buffer.append(stripped)
        i += 1

    flush_paragraph()
    flush_bullets()
    return sentences, had_code, had_prose


# ---------------------------------------------------------------------------
# Podcast-script generation
# ---------------------------------------------------------------------------

def chapter_number(idx):
    return NUMBER_WORDS[idx] if idx < len(NUMBER_WORDS) else str(idx + 1)


def build_narration(title, intro_text, sections):
    clean_title = clean_inline_markdown(title) or "this project"
    teaser = clean_prose_block(intro_text)

    parts = [
        "Hey everyone, welcome back to Build Log — the show where we pop the hood on a "
        "project and walk through exactly how it came together, step by step. Today's "
        f"episode: {clean_title}. "
        + (f"{teaser} " if teaser else "")
        + "So get comfortable, and let's dive into how this one got built."
    ]

    for idx, (heading, body_lines) in enumerate(sections):
        clean_heading = clean_inline_markdown(re.sub(r"^\d+\.\s*", "", heading))
        sentences, had_code, had_prose = section_body_to_sentences(body_lines)

        lead_in = LEAD_INS[idx % len(LEAD_INS)]
        chunk = f"{lead_in} Chapter {chapter_number(idx)}: {clean_heading}."
        if sentences:
            chunk += " " + " ".join(sentences)

        if had_code and not had_prose:
            chunk += (
                " Now, this part of the write-up is basically a wall of code and file "
                "names — and trust me, nobody wants to hear a file tree read aloud, so "
                "I'll just say: peek at the Markdown if you want the nitty-gritty details."
            )
        elif had_code:
            chunk += (
                " There's also a snippet in the written version worth a look if you're "
                "following along on screen — I'll spare your ears the ASCII art."
            )

        parts.append(chunk)

    parts.append(
        "And that's a wrap! From digging up the source material, to picking a home for "
        "the project, building out the page, and giving it a final once-over in the "
        "browser — that's the whole journey from blank folder to live site. Thanks so "
        "much for tuning in to Build Log. If you enjoyed this walkthrough, go check out "
        "the project for yourself, and we'll catch you on the next one!"
    )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# ElevenLabs Text-to-Speech
# ---------------------------------------------------------------------------

def chunk_text(text, max_chars=MAX_CHUNK_CHARS):
    """Split narration text into <= max_chars pieces, breaking on sentence/paragraph bounds."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    def push_current():
        nonlocal current
        if current:
            chunks.append(current)
            current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue

        push_current()
        if len(para) <= max_chars:
            current = para
            continue

        piece = ""
        for sentence in re.split(r"(?<=[.!?])\s+", para):
            cand = f"{piece} {sentence}".strip() if piece else sentence
            if len(cand) <= max_chars:
                piece = cand
            else:
                if piece:
                    chunks.append(piece)
                piece = sentence
        current = piece

    push_current()
    return chunks


def synthesize_chunk(text, api_key, voice_id, model_id, voice_settings):
    payload = json.dumps({
        "text": text,
        "model_id": model_id,
        "voice_settings": voice_settings,
    }).encode("utf-8")

    request = urllib.request.Request(TTS_URL.format(voice_id=voice_id), data=payload, method="POST")
    request.add_header("xi-api-key", api_key)
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "audio/mpeg")

    try:
        with urllib.request.urlopen(request) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"ElevenLabs API error {exc.code}: {details}") from exc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert a Markdown summary into a fun, podcast-style narration with ElevenLabs TTS."
    )
    parser.add_argument("markdown_file", help="Path to the Markdown file to narrate (e.g. SUMMARY.md)")
    parser.add_argument("-o", "--output", default="narration.mp3", help="Where to write the generated audio (default: narration.mp3)")
    parser.add_argument("--script-out", help="Also save the generated narration script as a text file")
    parser.add_argument("--script-only", action="store_true", help="Only generate (and print/save) the script — skip the ElevenLabs API call")
    parser.add_argument("--voice-id", default=os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID), help="ElevenLabs voice ID to narrate with")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="ElevenLabs TTS model ID")
    parser.add_argument("--stability", type=float, default=0.45, help="Voice stability 0-1 (lower = more expressive/varied delivery)")
    parser.add_argument("--similarity-boost", type=float, default=0.75, help="Voice similarity boost 0-1")
    parser.add_argument("--style", type=float, default=0.35, help="Style exaggeration 0-1 (higher = more animated, podcast-y delivery)")
    args = parser.parse_args()

    with open(args.markdown_file, "r", encoding="utf-8") as handle:
        raw_text = handle.read()

    title, intro_text, sections = parse_markdown(raw_text)
    script = build_narration(title, intro_text, sections)

    print(f"--- Generated narration script ({len(script):,} characters) ---\n")
    print(script)
    print()

    if args.script_out:
        with open(args.script_out, "w", encoding="utf-8") as handle:
            handle.write(script)
        print(f"Saved narration script to {args.script_out}\n")

    if args.script_only:
        return

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit(
            "ERROR: Set the ELEVENLABS_API_KEY environment variable with your ElevenLabs "
            "API key, or rerun with --script-only to just preview the script."
        )

    voice_settings = {
        "stability": args.stability,
        "similarity_boost": args.similarity_boost,
        "style": args.style,
        "use_speaker_boost": True,
    }

    chunks = chunk_text(script)
    print(f"Synthesizing audio in {len(chunks)} chunk(s) with voice '{args.voice_id}' ...")

    # Each chunk comes back as a complete, independent MP3 stream. Plain
    # concatenation of those streams plays back fine in virtually every
    # player/browser, so we avoid pulling in ffmpeg just to stitch audio.
    audio_bytes = bytearray()
    for index, chunk in enumerate(chunks, start=1):
        print(f"  -> chunk {index}/{len(chunks)} ({len(chunk)} chars)")
        audio_bytes.extend(synthesize_chunk(chunk, api_key, args.voice_id, args.model_id, voice_settings))

    with open(args.output, "wb") as handle:
        handle.write(audio_bytes)

    print(f"\nDone! Wrote {len(audio_bytes):,} bytes of audio to {args.output}")


if __name__ == "__main__":
    main()

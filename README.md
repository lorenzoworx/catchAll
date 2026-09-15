# CatchAll

[![Verify](https://github.com/lorenzoworx/catchAll/actions/workflows/verify.yml/badge.svg)](https://github.com/lorenzoworx/catchAll/actions/workflows/verify.yml)

CatchAll is a local-first live-caption prototype. It keeps the original transcript visible, clearly separates provisional text from finalized text, and offers an optional plain-language view without replacing the speaker's words.

## What it does

- Captures microphone audio in the browser and prepares mono 16 kHz frames in an audio worklet.
- Transcribes English speech locally with `faster-whisper`.
- Shows the recognizer's latest guess as provisional text and moves stable words into an append-only finalized transcript.
- Finalizes the remaining phrase when the microphone stops or a speech boundary is detected.
- Optionally rewrites finalized sentences in plainer language, with checks for meaning, negation, names, numbers, and dates.
- Exports finalized verbatim and accepted plain-language captions as a text file.
- Reconnects after a local server interruption while preserving the finalized browser transcript and user preference.

CatchAll does not persist audio or transcripts. Models and caption processing run on the machine hosting the server.

## Why two caption lanes?

Live captions become difficult to follow when earlier text changes unexpectedly or when correct words are still hard to process quickly. CatchAll assigns a different responsibility to each lane:

- **Verbatim captions** are the closest transcription of what was said. Only the trailing provisional phrase may change; finalized words are not edited afterward.
- **Plain-language captions** are optional and additive. Only finalized sentences are considered for rewriting. When a candidate fails a safety check, CatchAll displays the original sentence instead.

The automated checks reduce risk, but they cannot guarantee that every rewrite preserves meaning. The verbatim lane remains authoritative.

## Local setup

Prerequisites:

- Python 3.12 or newer
- A C++20 compiler and CMake 3.26 or newer
- Node.js 20 or newer for browser tests and linting

Create the environment and install the application:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev,simplification]'
npm install
```

Start the local server:

```bash
.venv/bin/uvicorn catchall.app:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The first connection downloads the configured Whisper model. The plain-language entailment model is downloaded only when that feature first processes a sentence.

Microphone capture requires localhost or HTTPS and a browser with `getUserMedia`, `AudioContext`, and audio-worklet support.

## Recognition configuration

The default remains `tiny.en` on CPU with `int8` computation. Override it only when comparing a deliberate configuration:

```bash
CATCHALL_WHISPER_MODEL=base.en \
CATCHALL_WHISPER_DEVICE=cpu \
CATCHALL_WHISPER_COMPUTE_TYPE=int8 \
.venv/bin/uvicorn catchall.app:app
```

The current four-clip evaluation favored `tiny.en`: the latest capture-end run measured 0.2622 corpus word error rate, 769.69 ms median commit latency, and 143.11 ms median capture-finalization latency, with no post-commit retractions. See [the model comparison](evaluation/results/model-comparison.md), [capture-end comparison](evaluation/results/capture-end-comparison.md), and [manual browser acceptance](evaluation/results/manual-browser-acceptance.md) for scope and caveats.

## Verification

Run the Python, browser-module, style, and native tests:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
npm run test:js
npm run lint:js
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

## Streaming evaluation

Evaluation clips use matching `.wav` and `.txt` filenames. Private audio is ignored by Git; committed transcripts and corpus notes document the current test set.

With the server running, evaluate the complete browser-to-WebSocket caption path in real time:

```bash
.venv/bin/python -m evaluation.run_streaming
```

By default, the runner trims trailing silence and sends the same explicit capture-end signal as the browser. Use `--keep-trailing-silence` only for a deliberate comparison.

## Architecture

```text
Browser microphone
    -> audio worklet and resampler
    -> WebSocket audio frames
    -> native C++ ring buffer
    -> speech boundary detection
    -> faster-whisper recognition
    -> local-agreement finalization
    -> verbatim captions
    -> optional guarded plain-language captions
```

## Current limits

- English only
- No speaker identification or diarization
- No meeting-platform integrations
- No accounts, cloud sync, or stored transcript history
- Prototype-scale local use rather than production traffic
- Automated rewrite checks cannot guarantee equivalent meaning

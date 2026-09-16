# Changelog

## 0.1.0 - 2026-09-15

First complete local-first prototype milestone.

- Captures browser microphone audio and transcribes English speech locally with
  `tiny.en` as the default recognizer.
- Separates append-only finalized captions from provisional text and finalizes
  the remaining phrase at speech or capture boundaries.
- Provides optional guarded plain-language captions without replacing the
  verbatim transcript.
- Preserves browser transcript state across server reconnections and supports
  finalized transcript export and explicit clearing.
- Handles unsupported capture environments, microphone failures, malformed
  protocol messages, and bounded audio backpressure without changing finalized
  text.
- Includes responsive keyboard-accessible controls, automated Python,
  JavaScript, and native tests, streaming evaluation, and continuous
  integration.

The rejected catch-up recognition queue experiment is not part of this
release.

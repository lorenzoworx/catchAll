# Final prototype acceptance

Date: 2026-09-15

This pass verifies the CatchAll 0.1.0 local-first prototype milestone. It uses
the default `tiny.en` recognizer on CPU with `int8` computation. The existing
four-clip corpus was streamed in real time through the WebSocket audio and
explicit capture-finalization path. Results were written to a temporary
location so the accepted comparison artifact remained unchanged.

## Browser acceptance

| Check | Result | Evidence |
| --- | --- | --- |
| Initial readiness | Pass | The page reached `Connected`, reported `Microphone ready`, and enabled the microphone control. |
| Release metadata | Pass | The description, theme color, and SVG favicon loaded; the favicon returned HTTP 200 without the earlier 404. |
| Plain-language preference | Pass | Enabling the optional lane round-tripped through the server and returned an enabled control. |
| Reconnect safety | Pass | Server loss disabled capture, discarded provisional text, and kept the requested plain-language preference visible. |
| Reconnect recovery | Pass | Restarting the server returned the page to ready state and restored the plain-language preference. |
| Mobile layout | Pass | At 390 px, the document had no horizontal overflow, controls were 358 px wide and 45 px tall, and both lanes fit the viewport. |

The earlier manual microphone acceptance remains the evidence for real browser
permission, audio-worklet capture, finalized captions, and transcript export.

## Automated verification

| Check | Result |
| --- | ---: |
| Python tests | 166 passed |
| JavaScript tests | 50 passed |
| Native C++ tests | 1 passed |
| Python lint and formatting | Pass |
| JavaScript lint | Pass |

## Streaming acceptance

| Metric | Result |
| --- | ---: |
| Clips | 4 |
| Corpus WER | 0.2622 |
| Commit latency p50 | 844.55 ms |
| Commit latency p90 | 1508.86 ms |
| Capture finalization p50 | 203.02 ms |
| Capture finalization p90 | 232.84 ms |
| Dropped samples | 0 |
| Rejected recognition windows | 0 |
| Duplicate boundaries | 0 |
| Post-commit retractions | 0 |

Quality matched the accepted capture-end baseline. Latency moved modestly in
this run but remained within the prototype's observed range, while every
stability invariant remained at zero.

## Decision

Accept version 0.1.0 as the completed local-first prototype milestone. Keep
`tiny.en` as the default recognizer. Do not reintroduce the rejected catch-up
queue experiment. Production traffic, additional languages, diarization,
meeting integrations, accounts, and stored history remain outside this
milestone.

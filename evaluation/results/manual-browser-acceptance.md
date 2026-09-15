# Manual browser acceptance

Date: 2026-09-15

This pass exercised CatchAll through the in-app browser against a fresh local
server. It used the default `tiny.en` model on CPU with `int8` computation. A
real microphone was used with explicit permission. Captured audio and
transcript text were not saved as evaluation artifacts.

| Check | Result | Evidence |
| --- | --- | --- |
| Server readiness | Pass | The page moved from connecting to connected and enabled the microphone control. |
| Microphone permission | Pass | The page waited for browser permission, then entered the recording state after approval. |
| Audio worklet | Pass | The page reported prepared 16 kHz audio continuously during capture. |
| Verbatim captions | Pass | Finalized captions accumulated while the microphone remained active. |
| Explicit stop finalization | Pass | Stopping returned the control to its idle state and left no provisional text. |
| Transcript export | Pass | Export became available and the page reported a successful finalized-transcript export. |
| Plain-language preference | Pass | The optional lane enabled independently and stayed enabled through the second capture. |
| Plain-language fallback behavior | Pass | The lane emitted three source-preserving `unchanged` results. |
| Recoverable-error alert | Pass | No capture alert appeared during either session. |
| Browser runtime | Pass | No browser warnings or errors were recorded. |
| Mobile layout | Pass | At 390 px wide, the page had no horizontal overflow, all session controls were 358 px wide and 45 px tall, and the caption lanes stacked vertically. |
| Desktop layout | Pass | At 1280 px wide, the page had no horizontal overflow and both 516 px caption lanes remained side by side. |
| Skip navigation | Pass | Activating “Skip to captions” moved keyboard focus to the live-caption region. |

## Observations

The prompted sentence was recognizably present in the verbatim output but was
not transcribed exactly. This is consistent with the existing `tiny.en`
evaluation rather than a capture or finalization failure.

The sentence intended to exercise a changed plain-language rewrite was not
transcribed faithfully enough to trigger the expected rule. This manual pass
therefore validates safe source-preserving output, not the visual presentation
of an accepted rewrite. Accepted, rejected, unchanged, and error fallback
paths remain covered by automated pipeline tests.

## Decision

The browser capture, stop-finalization, export, and safe optional-caption paths
are ready to retain. Keep `tiny.en` as the default. Do not reintroduce the
rejected catch-up queue experiment.

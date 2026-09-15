# Noise robustness experiment

Date: 2026-09-15

This experiment followed the manual browser observation of repeated low-value
captions during a live microphone session. It tested whether a conservative
recognizer-level hallucination control could reduce that risk without harming
the accepted streaming baseline.

## Synthetic signal probe

Five deterministic three-second signals were checked against the existing
energy speech gate and the default `tiny.en` recognizer.

| Signal | RMS | Gate | Recognizer output |
| --- | ---: | --- | --- |
| Silence | 0.0000 | Skipped | Not evaluated |
| Quiet white noise | 0.0050 | Skipped | Not evaluated |
| White noise above threshold | 0.0121 | Accepted | Empty |
| Louder white noise | 0.0200 | Accepted | Empty |
| 60 Hz hum | 0.0141 | Accepted | Empty |

The current pipeline did not produce false captions for synthetic silence,
white noise, or electrical hum. Raising the energy threshold was therefore not
justified and could remove useful distant speech.

## Hallucination-silence candidate

The candidate set Faster Whisper's `hallucination_silence_threshold` to two
seconds. It was evaluated with the same four private clips, real-time pacing,
CPU execution, `int8` computation, and `tiny.en` model as the accepted
capture-end baseline.

| Metric | Accepted baseline | Candidate |
| --- | ---: | ---: |
| Corpus WER | 0.2622 | 0.2683 |
| Clean-close WER | 0.221 | 0.234 |
| Fast-jargon WER | 0.405 | 0.418 |
| Noisy-distant WER | 0.141 | 0.141 |
| Pauses-repetitions WER | 0.287 | 0.287 |
| Commit latency p50 | 769.69 ms | 956.14 ms |
| Commit latency p90 | 1453.05 ms | 2092.08 ms |
| Capture finalization p50 | 143.11 ms | 224.48 ms |
| Capture finalization p90 | 170.75 ms | 1250.35 ms |
| Rejected recognition windows | 0 | 22 |
| Post-commit retractions | 0 | 0 |

## Decision

Reject the candidate. It worsened accuracy, latency, capture finalization, and
recognition backpressure without improving the noisy-distant clip. Keep the
existing energy gate and Faster Whisper options.

The manual observation cannot be reproduced from the synthetic signals, and
the microphone audio was intentionally not retained. A future suppression
change requires a consented, reproducible false-caption clip before changing
runtime behavior.

Keep `tiny.en` as the default. Do not reintroduce the rejected catch-up queue
experiment.

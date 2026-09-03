# Whisper model comparison

Both models were evaluated using the same four-clip corpus, real-time
audio pacing, CPU execution, and `int8` computation.

| Metric | tiny.en | base.en |
| --- | ---: | ---: |
| Corpus WER | 0.2774 | 0.3201 |
| Clean-close WER | 0.208 | 0.234 |
| Fast-jargon WER | 0.443 | 0.304 |
| Noisy-distant WER | 0.141 | 0.482 |
| Pauses-repetitions WER | 0.322 | 0.253 |
| Commit latency p50 | 799.12 ms | 1038.68 ms |
| Commit latency p90 | 1680.82 ms | 1398.55 ms |
| Rejected recognition windows | 0 | 5 |
| Duplicate boundaries | 0 | 0 |
| Post-commit retractions | 0 | 0 |

## Decision

`tiny.en` remains the default. `base.en` improved jargon and paused
speech, but produced worse overall accuracy, substantially worse noisy
speech, higher median latency, and five rejected recognition windows.

The lower `base.en` p90 latency is not treated as a speed improvement
because rejected windows produce no latency observation.

A catch-up queue prototype replaced two stale windows but still skipped
five windows overall and did not change any per-clip WER result. It was
therefore not retained.
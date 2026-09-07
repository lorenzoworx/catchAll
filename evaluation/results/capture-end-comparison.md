# Capture-end evaluation

The streaming evaluator now trims trailing frames below the speech gate's
RMS threshold and ends each clip with the same `capture_end` control message
used by the browser. It waits for the server's `finalized` acknowledgment
instead of appending two seconds of synthetic silence and waiting a fixed six
seconds. The committed source recordings are not modified.

Both runs used the same four-clip corpus, real-time pacing, CPU execution,
`int8` computation, and the `tiny.en` model. The earlier result used the
synthetic-silence completion behavior; the new result uses `capture_end`.

| Metric | Earlier tiny.en | capture_end |
| --- | ---: | ---: |
| Corpus WER | 0.2774 | 0.2622 |
| Clean-close WER | 0.208 | 0.221 |
| Fast-jargon WER | 0.443 | 0.405 |
| Noisy-distant WER | 0.141 | 0.141 |
| Pauses-repetitions WER | 0.322 | 0.287 |
| Commit latency p50 | 799.12 ms | 769.69 ms |
| Commit latency p90 | 1680.82 ms | 1453.05 ms |
| Capture finalization p50 | not measured | 143.11 ms |
| Capture finalization p90 | not measured | 170.75 ms |
| Rejected recognition windows | 0 | 0 |
| Duplicate boundaries | 0 | 0 |
| Post-commit retractions | 0 | 0 |

## Interpretation

The evaluator removed between 21.56 ms and 1984.75 ms of trailing silence per
clip. All four clips then required exactly one explicit capture boundary. The
explicit completion path did not regress the measured stability invariants,
did not introduce recognition backpressure, and finalized every clip within
170.75 ms.

The lower corpus WER is encouraging, but it should not be attributed entirely
to capture-end finalization because the end condition changed between runs.
A purpose-built short-utterance corpus would still broaden coverage beyond the
short-capture integration tests.

## Decision

Keep `tiny.en` as the default and retain the bounded FIFO recognition queue.
Use the `capture_end` evaluator for future streaming measurements. Do not
reintroduce the rejected catch-up queue experiment.

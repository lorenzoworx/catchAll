# CatchAll evaluation corpus

Each evaluation clip uses two files with the same stem:

- `clip-name.wav`: 16 kHz, mono, signed 16-bit PCM WAV
- `clip-name.txt`: a human-corrected verbatim transcript

Reference transcripts must include repetitions, false starts, and filler
words that were actually spoken. Do not use an uncorrected machine
transcript as the reference.

## Initial coverage

The baseline should contain at least one 20–60 second clip for each condition:

1. Clean, close microphone
2. Non-native or accented English
3. Pauses, repetitions, and false starts
4. Background noise or a distant microphone
5. Fast speech with technical terms or acronyms
6. Two speakers with consent, if available

## Privacy and licensing

Do not commit recordings of real meetings or anyone who has not explicitly
consented to redistribution.

Private recordings may remain outside the repository and be passed to the
evaluation command by directory path. Public corpus audio must retain its
required attribution and license information.

For every clip, record the microphone, room, speaker condition, and source
in `NOTES.md`.
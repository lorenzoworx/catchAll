# Catch All
Real-time captions with finalized text that stays finalized, plus an optional plain-language view beside the original transcript.

## The problem
The people who depend most on live captions include deaf and hard-of-hearing users, non-native English speakers, and peopls with cognitive disabilities or attention differences. They need to follow a conversation while it is happening. A transcript delivered afterward solves a different problem.

Live captions can be difficult to follow when:
- Previously displayed text changes unexpectedly
- Captions arrive too late to follow the conversation
- An accurate transcript sitt uses languate that is difficult to process quickly

## The idea
Catch All presents two caption lanew with different responsibilities

### Verbatim lane
The verbatim lane displays the speech regognizer's closest transcription of what was said. Every word is in one of two states:
- **Provisional**: The recognizer's current best guess. It appears only at the end of the transcript, is visually distinguished, and may change.

- **Finalized**: Text that has been accepted into the permanent transcrip. It will not be changed afterward.

Only finalized text enters transcript history, is exported, or is sent for plain-language rewriting.

The initial stability strategy compares consecutive transcription windows. A shared prefis is finalized only when both windows agree on it. This deliberately trades some latency for greater visual stability.

A core evaluation goal is to measure whether this prevents post-finalization retractions without making captions unacceptably slow.

### Plain-language lane
The plain language lane is optional, additive, and never authoritative. It appears in a seperately labelled column and only processes finalized text. Users can disable it without disabling verbatim captions.
Because rewriting can accidentally change meaning, each candidate rewrite is checked before display:
- Numbers, dates, and names should be preserved
- Negations should not be added or removed
- The rewrite must stay semantically close to the original.

These checks reduce risk but cannot guarantee equivalent meaning. If a rewrite fails a check or cannot be produced, the application displays the original text instead.

The user can therefore choose between two presentations without losing access to the source transcript.

## First milestone
Build a FastAPI server that:
- Serves one accessible web page
- Exposes a health endpoint
- Can be started and tested locally

## Planned architecture
Browser audio -> WebSocken -> c++ audio buffer -> Speech recognition -> Caption stability -> Browser display

## Non-goals for V1
- Languages other than English
- Speaker identification or diarization
- Meeting platform integrations
- User accounts or stored transcripts
- Training a custom speech-recognition model
- Supporting large-scale production traffic
- Guaranteeing that an automated rewrite preserves meaning
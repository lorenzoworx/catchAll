import struct
from collections.abc import Sequence
from typing import Any

from fastapi.testclient import TestClient

from catchall.app import app
from catchall.audio_protocol import AUDIO_FRAME_TYPE, AUDIO_HEADER
from catchall.recognition import RecognitionHypothesis, TimedWord
from catchall.recognizer_provider import RecognizerProvider


class FakeRecognizer:
    def transcribe(self, samples: Sequence[float]) -> RecognitionHypothesis:
        midpoint = len(samples) // 2
        
        return RecognitionHypothesis(
            words=(
                TimedWord(
                    text="test",
                    start_sample=0,
                    end_sample=midpoint
                ),
                TimedWord(
                    text="caption",
                    start_sample=midpoint,
                    end_sample=len(samples)
                ),
            )
        )

app.state.recognizer_provider = RecognizerProvider(
    FakeRecognizer
)

client = TestClient(app)

def receive_startup_messages(websocket: Any) -> None:
    assert websocket.receive_json() == {
        "type": "connection",
        "status": "connected",
    }
    assert websocket.receive_json() == {
        "type": "recognizer",
        "status": "loading",
    }
    assert websocket.receive_json() == {
        "type": "recognizer",
        "status": "ready",
    }

def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_homepage() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<html lang="en">' in response.text
    assert "<h1>CatchAll</h1>" in response.text
    assert 'role="status"' in response.text
    assert 'aria-live="polite"' in response.text
    assert "verbatim captions" in response.text.lower()
    assert "plain-language captions" in response.text.lower()
    assert 'id="microphone-button"' in response.text
    assert "disabled" in response.text
    assert 'id="recording-status"' in response.text
    assert 'id="finalized-captions"' in response.text
    assert 'id="provisional-caption"' in response.text
    assert 'id="plain-language-toggle"' in response.text
    assert 'id="plain-language-status"' in response.text
    assert 'id="plain-language-captions"' in response.text
    assert "processed locally" in response.text
    assert 'id="export-button"' in response.text
    assert 'id="export-status"' in response.text

def test_stylesheet() -> None:
    response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]

def test_websocket_connects() -> None:
    with client.websocket_connect("/ws") as websocket:
        receive_startup_messages(websocket)

def test_websocket_ping_pong() -> None:
    with client.websocket_connect("/ws") as websocket:
        receive_startup_messages(websocket)
        websocket.send_json({"type": "ping"})

        assert websocket.receive_json() == {"type": "pong"}

def test_javascript_is_served() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert '"plain_language"' in response.text
    assert '"plain_caption"' in response.text

def test_websocket_consumes_binary_audio() -> None:
    samples = [0] * 320
    header = AUDIO_HEADER.pack(
        AUDIO_FRAME_TYPE,
        0,
        len(samples),
        0,
    )
    payload = header + struct.pack(f"<{len(samples)}h", *samples)

    with client.websocket_connect("/ws") as websocket:
        receive_startup_messages(websocket)
        websocket.send_bytes(payload)
        websocket.send_json({"type": "stats"})

        assert websocket.receive_json() == {
            "type": "stats",
            "received_samples": 320,
            "consumed_samples": 320,
            "buffered_samples": 0,
            "buffered_seconds": 0.0,
            "dropped_samples": 0,
            "rejected_frames": 0,
            "pending_recognition_windows": 0,
            "rejected_recognition_windows": 0,
            "failed_recognition_windows": 0,
            "skipped_silence_windows": 0,
            "committed_words": 0,
            "final_silence_windows": 0,
            "silence_boundaries": 0,
            "plain_language_enabled": False,
            "processed_plain_sentences": 0,
            "fallback_plain_sentences": 0,
            "rejected_plain_sentences": 0
        }

def test_websocket_rejects_invalid_audio_frame() -> None:
    with client.websocket_connect("/ws") as websocket:
        receive_startup_messages(websocket)
        websocket.send_bytes(b"\x01")

        message = websocket.receive_json()

        assert message["type"] == "error"
        assert message["code"] == "invalid_audio_frame"

def test_audio_worklet_is_served() -> None:
    response = client.get("/static/capture-worklet.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]

def test_browser_audio_protocol_module_is_served() -> None:
    response = client.get("/static/audio-protocol.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]

def test_websocket_emits_provisional_caption() -> None:
    samples = [12_000] * 320

    with client.websocket_connect("/ws") as websocket:
        receive_startup_messages(websocket)

        for frame_number in range(50):
            header = AUDIO_HEADER.pack(
                AUDIO_FRAME_TYPE,
                0,
                len(samples),
                frame_number * len(samples),
            )
            payload = header + struct.pack(
                f"<{len(samples)}h",
                *samples,
            )

            websocket.send_bytes(payload)

        assert websocket.receive_json() == {
            "type": "caption",
            "state": "provisional",
            "text": "test caption",
            "window_start_sample": 0,
            "window_end_sample": 16_000,
        }

def test_websocket_commits_stable_caption_prefix() -> None:
    samples = [12_000] * 320

    with client.websocket_connect("/ws") as websocket:
        receive_startup_messages(websocket)

        for frame_number in range(75):
            header = AUDIO_HEADER.pack(
                AUDIO_FRAME_TYPE,
                0,
                len(samples),
                frame_number * len(samples),
            )
            payload = header + struct.pack(
                f"<{len(samples)}h",
                *samples,
            )

            websocket.send_bytes(payload)

        first = websocket.receive_json()
        committed = websocket.receive_json()
        provisional = websocket.receive_json()

        assert first == {
            "type": "caption",
            "state": "provisional",
            "text": "test caption",
            "window_start_sample": 0,
            "window_end_sample": 16_000,
        }

        assert committed == {
            "type": "caption",
            "state": "committed",
            "text": "test caption",
            "start_sample": 0,
            "end_sample": 16_000,
        }

        assert provisional == {
            "type": "caption",
            "state": "provisional",
            "text": "",
            "window_start_sample": 0,
            "window_end_sample": 24_000,
        }

def test_silence_runs_final_recognition_pass() -> None:
    active_samples = [12_000] * 320
    silent_samples = [0] * 320

    with client.websocket_connect("/ws") as websocket:
        receive_startup_messages(websocket)

        for frame_number in range(50):
            header = AUDIO_HEADER.pack(
                AUDIO_FRAME_TYPE,
                0,
                len(active_samples),
                frame_number * len(active_samples),
            )
            payload = header + struct.pack(
                f"<{len(active_samples)}h",
                *active_samples,
            )
            websocket.send_bytes(payload)

        for frame_number in range(50, 75):
            header = AUDIO_HEADER.pack(
                AUDIO_FRAME_TYPE,
                0,
                len(silent_samples),
                frame_number * len(silent_samples)
            )

            payload = header + struct.pack(
                f"<{len(silent_samples)}h",
                *silent_samples,
            )
            websocket.send_bytes(payload)

        first = websocket.receive_json()
        committed = websocket.receive_json()
        provisional = websocket.receive_json()

        assert first == {
            "type": "caption",
            "state": "provisional",
            "text": "test caption",
            "window_start_sample": 0,
            "window_end_sample": 16_000
        }

        assert committed == {
            "type": "caption",
            "state": "committed",
            "text": "test caption",
            "start_sample": 0,
            "end_sample": 16_000
        }

        assert provisional == {
            "type": "caption",
            "state": "provisional",
            "text": "",
            "window_start_sample": 0,
            "window_end_sample": 24_000
        }

def test_plain_language_is_optional() -> None:
    with client.websocket_connect("/ws") as websocket:
        receive_startup_messages(websocket)

        websocket.send_json({
            "type": "plain_language",
            "enabled": True
        })

        assert websocket.receive_json() == {
            "type": "plain_language",
            "enabled": True,
            "processing": "local"
        }

        websocket.send_json({
            "type": "plain_language",
            "enabled": False
        })

        assert websocket.receive_json() == {
            "type": "plain_language",
            "enabled": False,
            "processing": "local"
        }

def test_plain_language_setting_requires_boolean() -> None:
    with client.websocket_connect("/ws") as websocket:
        receive_startup_messages(websocket)

        websocket.send_json({
            "type": "plain_language",
            "enabled": "yes"
        })

        assert websocket.receive_json() == {
            "type": "error",
            "code": "invalid_plain_language_setting",
            "message": "enabled must be a boolean."
        }

def test_transcript_export_javascript_is_served() -> None:
    response = client.get("/static/transcript-export.js")

    assert response.status_code == 200
    assert "buildTranscriptDocument" in response.text
    assert "formatTranscriptText" in response.text
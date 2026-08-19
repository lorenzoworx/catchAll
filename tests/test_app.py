import struct
from collections.abc import Sequence
from typing import Any

from fastapi.testclient import TestClient

from catchall.app import app
from catchall.audio_protocol import AUDIO_FRAME_TYPE, AUDIO_HEADER
from catchall.recognizer_provider import RecognizerProvider


class FakeRecognizer:
    def transcribe(self, samples: Sequence[float]) -> str:
        return "test caption"

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
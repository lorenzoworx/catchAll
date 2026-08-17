import struct

from fastapi.testclient import TestClient

from catchall.app import app
from catchall.audio_protocol import AUDIO_FRAME_TYPE, AUDIO_HEADER

client = TestClient(app)

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
    assert 'id="recording-status"' in response.text

def test_stylesheet() -> None:
    response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]

def test_websocket_connects() -> None:
    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()

        assert message == {
            "type": "connection",
            "status": "connected",
        }

def test_websocket_ping_pong() -> None:
    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "ping"})

        assert websocket.receive_json() == {"type": "pong"}

def test_javascript_is_served() -> None:
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]

def test_websocket_writes_binary_audio_to_ring() -> None:
    samples = [0] * 320
    header = AUDIO_HEADER.pack(
        AUDIO_FRAME_TYPE,
        0,
        len(samples),
        0,
    )
    payload = header + struct.pack(f"<{len(samples)}h", *samples)

    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()
        websocket.send_bytes(payload)
        websocket.send_json({"type": "stats"})

        assert websocket.receive_json() == {
            "type": "stats",
            "buffered_samples": 320,
            "dropped_samples": 0,
        }

def test_websocket_rejects_invalid_audio_frame() -> None:
    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()
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
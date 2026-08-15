import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from catchall import _core
from catchall.audio_protocol import AudioFrameError, decode_audio_frame

SAMPLE_RATE = 16_000
RING_SECONDS = 10
RING_CAPACITY = SAMPLE_RATE * RING_SECONDS

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="CatchAll")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/", include_in_schema=False)
def inded() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

@app.websocket("/ws")
async def caption_socket(websocket: WebSocket) -> None:
    ring = _core.AudioRing(RING_CAPACITY)

    await websocket.accept()
    await websocket.send_json(
        {
            "type": "connection",
            "status": "connected",
        }
    )

    try:
        while True:
            incoming = await websocket.receive()

            if incoming["type"] == "websocket.disconnect":
                break

            binary = incoming.get("bytes")

            if binary is not None:
                try:
                    frame = decode_audio_frame(binary)
                except AudioFrameError as error:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "invalid_audio_frame",
                            "message": str(error),
                        }
                    )
                    continue

                accepted = ring.write(frame.samples)

                if accepted != len(frame.samples):
                    await websocket.send_json(
                       {
                            "type": "error",
                            "code": "audio_buffer_full",
                            "dropped_samples": len(frame.samples) - accepted,
                        }
                    )
                continue

            text = incoming.get("text")

            if text is None:
                continue

            try:
                message = json.loads(text)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_json",
                        "message": "Control message is not valid JSON."
                    }
                )
                continue

            text = incoming.get("text")

            if text is None:
                continue

            try:
                message = json.loads(text)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_json",
                        "message": "Control message is not valid JSON."
                    }
                )
                continue

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "stats":
                await websocket.send_json(
                    {
                        "type": "stats",
                        "buffered_samples": ring.size,
                        "dropped_samples": ring.dropped_samples,
                    }
                )
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "unknown_message",
                        "message": "Unknown message type.",
                    }
                )
    except WebSocketDisconnect:
        pass

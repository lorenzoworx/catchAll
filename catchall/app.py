from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "connection",
            "status": "connected",
        }
    )

    try:
        while True:
            message = await websocket.receive_json()

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Unknown message type.",
                    }
                )
    except WebSocketDisconnect:
        pass
from pathlib import Path

from fastapi import FastAPI
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
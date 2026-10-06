import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parent / ".env")

from .simulator import router as simulator_router
from .broadcast import router as broadcast_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[startup] Bot ready -> http://localhost:8001/test", flush=True)
    yield


app = FastAPI(title="Krushi Mitra WhatsApp Bot", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"]
)
app.include_router(simulator_router)
app.include_router(broadcast_router)

if os.environ.get("WHATSAPP_TOKEN") and os.environ.get("PHONE_NUMBER_ID"):
    from .webhook import router as webhook_router
    app.include_router(webhook_router)
    print("[startup] Real WhatsApp webhook enabled.", flush=True)
else:
    print("[startup] SIMULATOR mode only.", flush=True)


@app.get("/health")
def health():
    return {"status": "ok", "service": "krushi-mitra-whatsapp-bot"}

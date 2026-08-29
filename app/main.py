"""
Krushi Mitra Backend - FastAPI Application

Run locally:
    cd e:\krushi-mitra
    uvicorn app.main:app --reload

Then visit http://127.0.0.1:8000/docs for interactive API docs (auto-generated
by FastAPI).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import schemes, eligibility, admin, search

app = FastAPI(
    title="Krushi Mitra API",
    description="Maharashtra farmer scheme discovery & eligibility API",
    version="0.1.0",
)

# Vite's default dev server ports. Tighten this to your real deployed
# frontend origin(s) before going anywhere near production.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schemes.router)
app.include_router(eligibility.router)
app.include_router(admin.router)
app.include_router(search.router)


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "krushi-mitra-backend"}

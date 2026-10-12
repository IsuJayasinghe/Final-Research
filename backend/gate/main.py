from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import ml_models
from router import router as gate_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ml_models.load_models()
    yield


app = FastAPI(title="Gate Appointment System API (Component 4)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gate_router)


@app.get("/")
def health():
    return {"status": "ok", "service": "gate-appointment-system-api"}

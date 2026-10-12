from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import documents
import ml_models
import noshow
import service
from repository import get_repository
from router import router as gate_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ml_models.load_models()
    noshow.load_model()
    service.init(get_repository())
    try:
        documents.warm_up()  # load the OCR model now so the first upload is not slow
    except ImportError:
        pass  # OCR is optional; /api/documents/check reports 503 if it is missing
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
    return {
        "status": "ok",
        "service": "gate-appointment-system-api",
        "storage": service.get_service().repo.kind,
    }

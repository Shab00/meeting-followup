from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.db import init_db
from app.routes import workflows


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # create Workflow table
    yield


app = FastAPI(title="Meeting Followup", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = workflows.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(workflows.router)


@app.get("/health")
def health():
    return {"status": "ok"}

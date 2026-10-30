from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.db import init_db
from app.routes import workflows


ALLOWED_ORIGINS = [
    "https://shab00.github.io",
    "http://localhost:4000",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()   # create Workflow table
    yield


app = FastAPI(title="Meeting Followup", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# CORS handling
# ---------------------------------------------------------------------------
# CORSMiddleware is deliberately not used here — same reasoning as
# meeting-chat. On this deployment it only supported a single origin via
# settings.allowed_origin and returned 400 'Disallowed CORS origin' on
# preflight requests from other origins.
#
# CORS is handled explicitly:
#   1. @app.options("/workflows") — 204 for known origins, 403 otherwise.
#   2. @app.middleware("http") — attaches Allow-Origin to every non-preflight
#      response from known origins.
# ---------------------------------------------------------------------------


@app.options("/workflows")
async def workflows_options(request: Request) -> Response:
    origin = request.headers.get("origin", "")
    if origin not in ALLOWED_ORIGINS:
        return Response(status_code=403, content="Origin not allowed")
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
            "Vary": "Origin",
        },
    )


@app.middleware("http")
async def _attach_cors(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


app.state.limiter = workflows.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(workflows.router)


@app.get("/health")
def health():
    return {"status": "ok"}

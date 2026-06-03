import os
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

SERVICE_NAME = os.getenv("SERVICE_NAME", "iot-ingestion")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.4.0")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")

app = FastAPI(
    title="FIT4110 Lab 04 - Smart Campus Operations Platform",
    version=SERVICE_VERSION,
    description="Service đóng gói chuẩn Docker phục vụ Ingestion IoT Metric theo đúng OpenAPI contract."
)


class SensorReadingCreate(BaseModel):
    device_id: str = Field(..., min_length=3, examples=["ESP32-LAB-A01"])
    metric: str = Field(..., examples=["temperature"])
    value: float = Field(..., description="Boundary dùng trong bài: -40 đến 80")
    unit: str = Field(..., examples=["celsius"])
    timestamp: str = Field(..., examples=["2026-05-13T08:30:00+07:00"])

    @field_validator("value")
    @classmethod
    def check_boundary(cls, v: float) -> float:
        if v < -40.0 or v > 80.0:
            raise ValueError("Value out of boundary range (-40 to 80)")
        return v


class SensorReading(SensorReadingCreate):
    reading_id: str
    created_at: str


class SensorReadingCreated(BaseModel):
    reading_id: str
    device_id: str
    metric: str
    accepted: bool
    created_at: str


METRICS_STORAGE: List[Dict] = []


def make_problem_response(
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    problem_type: str = "about:blank",
):
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": problem_type,
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    detail_msg = "Request validation failed."
    if errors:
        loc = ".".join(str(x) for x in errors[0].get("loc", []))
        msg = errors[0].get("msg", "")
        detail_msg = f"Invalid field '{loc}': {msg}. Check boundary values and data types."

    return make_problem_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        title="Validation error",
        detail=detail_msg,
        instance=str(request.url.path),
        problem_type="https://smart-campus.local/problems/validation-error",
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return make_problem_response(
        status_code=exc.status_code,
        title="Unauthorized" if exc.status_code == status.HTTP_401_UNAUTHORIZED else "HTTP Error",
        detail=str(exc.detail),
        instance=str(request.url.path),
        problem_type=(
            "https://smart-campus.local/problems/unauthorized"
            if exc.status_code == status.HTTP_401_UNAUTHORIZED
            else "https://smart-campus.local/problems/http-error"
        ),
    )


def verify_security_token(authorization: Optional[str] = Header(default=None)):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid bearer token",
        )
    expected = f"Bearer {AUTH_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid bearer token",
        )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
    }


def generate_reading_id() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    sequence = secrets.randbelow(10000)
    return f"R-{date_part}-{sequence:04d}"


@app.post(
    "/readings",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_security_token)],
)
async def create_reading(payload: SensorReadingCreate, response: Response):
    created_at = datetime.now(timezone.utc).isoformat()
    reading_id = generate_reading_id()
    record = {
        **payload.model_dump(),
        "reading_id": reading_id,
        "created_at": created_at,
    }
    METRICS_STORAGE.append(record)

    if payload.value == 80:
        response.headers["X-Warning"] = "High temperature boundary accepted"

    return SensorReadingCreated(
        reading_id=reading_id,
        device_id=payload.device_id,
        metric=payload.metric,
        accepted=True,
        created_at=created_at,
    )


@app.get(
    "/readings/latest",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_security_token)],
)
async def get_latest_readings(
    device_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
):
    items = [record for record in METRICS_STORAGE if device_id is None or record["device_id"] == device_id]
    items = sorted(items, key=lambda x: x["created_at"], reverse=True)[:limit]
    return {"items": items}


@app.get(
    "/readings/{reading_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_security_token)],
)
async def get_reading_by_id(reading_id: str):
    for record in METRICS_STORAGE:
        if record["reading_id"] == reading_id:
            return record
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Reading {reading_id} does not exist",
    )

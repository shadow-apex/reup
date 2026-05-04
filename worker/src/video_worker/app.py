from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from video_worker import __version__
from video_worker.errors import ContractError
from video_worker.jobs_store import JobRecord, store
from video_worker.pipeline import contract_error_from_exception, run_pipeline
from video_worker.settings import Settings, get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="reup-video-worker", version=__version__)


@app.exception_handler(HTTPException)
async def _http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "detail": None,
                "ffmpeg_exit_code": None,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request body",
                "detail": str(exc.errors())[:2000],
                "ffmpeg_exit_code": None,
            }
        },
    )


def ffmpeg_available(ffmpeg_path: str) -> bool:
    path = shutil.which(ffmpeg_path) if ffmpeg_path == "ffmpeg" else ffmpeg_path
    exe = path or ffmpeg_path
    try:
        r = subprocess.run(
            [exe, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@app.get("/health")
async def health(settings: Annotated[Settings, Depends(get_settings)]):
    return {
        "ok": True,
        "version": __version__,
        "ffmpeg_available": ffmpeg_available(settings.ffmpeg_path),
        "contract_version": "1",
    }


class JobCreateRequest(BaseModel):
    contract_version: str = Field(default="1")
    job_id: UUID
    input_video_path: str = Field(min_length=1)
    output_dir: str = Field(min_length=1)
    source_language: str = "zh"
    target_language: str = "vi"


def verify_secret(
    x_worker_secret: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_worker_secret or x_worker_secret != settings.worker_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or missing X-Worker-Secret",
                    "detail": None,
                    "ffmpeg_exit_code": None,
                }
            },
        )


def _http_error_payload(err: ContractError) -> dict:
    return {"error": err.as_dict()}


async def _process_job(job_id: str, settings: Settings) -> None:
    rec = await store.get(job_id)
    if not rec:
        return
    await store.update(job_id, status="processing", message="Running pipeline…")
    try:
        out_path, msg = await run_pipeline(
            job_id=job_id,
            input_video_path=rec.input_video_path,
            output_dir=rec.output_dir,
            source_language=rec.source_language,
            target_language=rec.target_language,
            settings=settings,
        )
        await store.update(
            job_id,
            status="completed",
            message=msg,
            output_video_path=out_path,
            error=None,
        )
    except BaseException as exc:
        logger.exception("Job %s failed", job_id)
        cerr = contract_error_from_exception(exc)
        await store.update(
            job_id,
            status="failed",
            message=None,
            output_video_path=None,
            error=cerr,
        )


@app.post("/v1/jobs", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_secret)])
async def create_job(
    body: JobCreateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
):
    if body.contract_version != "1":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Unsupported contract_version",
                    "detail": body.contract_version,
                    "ffmpeg_exit_code": None,
                }
            },
        )
    jid = str(body.job_id)
    existing = await store.get(jid)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "job_id already exists",
                    "detail": jid,
                    "ffmpeg_exit_code": None,
                }
            },
        )
    rec = JobRecord(
        job_id=jid,
        status="queued",
        message="Accepted",
        input_video_path=body.input_video_path,
        output_dir=body.output_dir,
        source_language=body.source_language,
        target_language=body.target_language,
    )
    await store.upsert(rec)
    asyncio.create_task(_process_job(jid, settings))
    return {
        "contract_version": "1",
        "job_id": jid,
        "status": "queued",
        "message": "Accepted; processing started",
    }


def _job_to_status_body(rec: JobRecord) -> dict:
    err = rec.error.as_dict() if rec.error else None
    return {
        "contract_version": "1",
        "job_id": rec.job_id,
        "status": rec.status,
        "message": rec.message,
        "output_video_path": rec.output_video_path,
        "error": err,
    }


@app.get("/v1/jobs/{job_id}", dependencies=[Depends(verify_secret)])
async def get_job(job_id: str):
    rec = await store.get(job_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Unknown job_id",
                    "detail": job_id,
                    "ffmpeg_exit_code": None,
                }
            },
        )
    return _job_to_status_body(rec)

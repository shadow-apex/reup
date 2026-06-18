from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from video_worker.errors import ContractError

logger = logging.getLogger(__name__)


@dataclass
class JobRecord:
    job_id: str
    status: str  # queued | processing | completed | failed
    message: str | None = None
    output_video_path: str | None = None
    error: "ContractError | None" = None
    input_video_path: str = ""
    output_dir: str = ""
    source_language: str = "zh"
    target_language: str = "vi"
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    vol_orig: float = 0.15  # 0.0 – 1.0, maps from GUI percentage


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def get(self, job_id: str) -> JobRecord | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def upsert(self, record: JobRecord) -> None:
        async with self._lock:
            self._jobs[record.job_id] = record

    async def update(self, job_id: str, **kwargs: Any) -> None:
        async with self._lock:
            rec = self._jobs.get(job_id)
            if not rec:
                return
            for k, v in kwargs.items():
                setattr(rec, k, v)


store = JobStore()

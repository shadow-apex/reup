import asyncio
import uuid
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from video_worker.app import app
from video_worker.settings import Settings, get_settings


@pytest.fixture
def override_settings(monkeypatch: pytest.MonkeyPatch):
    s = Settings(
        worker_secret="test-secret",
        pipeline_mode="stub",
        ffmpeg_timeout_seconds=120,
    )

    def _get() -> Settings:
        return s

    app.dependency_overrides[get_settings] = _get
    yield s
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(override_settings: Settings):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["contract_version"] == "1"


@pytest.mark.asyncio
async def test_jobs_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/v1/jobs", json={})
    assert r.status_code == 401
    body = r.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_job_stub_pipeline(
    override_settings: Settings,
    tiny_mp4: Path,
    silent_mp3: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    async def fake_tts(text: str, out_mp3: Path, voice: str) -> None:
        out_mp3.write_bytes(silent_mp3.read_bytes())

    monkeypatch.setattr("video_worker.pipeline._edge_tts_to_file", fake_tts)

    transport = ASGITransport(app=app)
    jid = str(uuid.uuid4())
    payload = {
        "contract_version": "1",
        "job_id": jid,
        "input_video_path": str(tiny_mp4.resolve()),
        "output_dir": str(out_dir.resolve()),
        "source_language": "zh",
        "target_language": "vi",
    }
    headers = {"X-Worker-Secret": "test-secret"}
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/v1/jobs", json=payload, headers=headers)
        assert r.status_code == 202
        for _ in range(200):
            gr = await ac.get(f"/v1/jobs/{jid}", headers=headers)
            assert gr.status_code == 200
            st = gr.json()["status"]
            if st in ("completed", "failed"):
                final = gr.json()
                break
            await asyncio.sleep(0.05)
        else:
            pytest.fail("job did not complete")

    assert final["status"] == "completed"
    assert final["output_video_path"]
    assert Path(final["output_video_path"]).is_file()

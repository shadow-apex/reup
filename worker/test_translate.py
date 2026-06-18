"""Quick test: run translate_text with the new prompt."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
sys.stdout.reconfigure(encoding="utf-8")  # Windows console fix

from video_worker.pipeline import translate_text
from video_worker.settings import Settings


async def main():
    settings = Settings()  # reads from .env
    text = "今天天气真好，我们一起去公园散步吧。"
    result = await translate_text(
        text=text,
        settings=settings,
        source="Chinese",
        target="Vietnamese",
    )
    print("=== TRANSLATED TEXT ===")
    print(result)
    print("=======================")


if __name__ == "__main__":
    asyncio.run(main())

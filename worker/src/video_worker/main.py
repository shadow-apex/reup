import uvicorn


def run() -> None:
    uvicorn.run(
        "video_worker.app:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":
    run()

from typing import Any


class ContractError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        detail: str | None = None,
        ffmpeg_exit_code: int | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail
        self.ffmpeg_exit_code = ffmpeg_exit_code

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
            "ffmpeg_exit_code": self.ffmpeg_exit_code,
        }

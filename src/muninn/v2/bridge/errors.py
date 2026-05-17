from __future__ import annotations


class BridgeError(RuntimeError):
    """Base error for structured v2 bridge failures."""

    def __init__(self, code: str, message: str | None = None, *, details: dict | None = None) -> None:
        super().__init__(message or code)
        self.code = str(code)
        self.message = str(message or code)
        self.details = dict(details or {})

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }

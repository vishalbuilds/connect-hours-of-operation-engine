from typing import Literal, Optional

Status = Literal["OPEN", "CLOSED", "HOLIDAY", "MEETING", "ERROR"]


class ResponseBuilder:

    @staticmethod
    def open(status: Status, message: str, payload: Optional[dict] = None) -> dict:
        return ResponseBuilder._build(status, message, payload)

    @staticmethod
    def closed(status: Status, message: str, payload: Optional[dict] = None) -> dict:
        return ResponseBuilder._build(status, message, payload)

    @staticmethod
    def error(status: Status, message: str, payload: Optional[dict] = None) -> dict:
        return ResponseBuilder._build(status, message, payload)

    @staticmethod
    def _build(status: Status, message: str, payload: Optional[dict]) -> dict:
        return {
            "status": status,
            "message": message,
            "payload": payload or {},
        }

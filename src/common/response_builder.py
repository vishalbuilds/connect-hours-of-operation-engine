from typing import Literal, Optional

Status = Literal["OPEN", "CLOSED", "HOLIDAY", "MEETING", "ERROR"]


class ResponseBuilder:

    @staticmethod
    def success(
        status: Status,
        message: str,
        payload: Optional[dict] = None,
        lambda_status="SUCCESS",
    ) -> dict:
        return ResponseBuilder._build(status, message, payload, lambda_status)

    @staticmethod
    def error(
        status: Status,
        message: str,
        payload: Optional[dict] = None,
        lambda_status="ERROR",
    ) -> dict:
        return ResponseBuilder._build(status, message, payload, lambda_status)

    @staticmethod
    def _build(
        status: Status, message: str, payload: Optional[dict], lambda_status
    ) -> dict:
        return {
            "lambda_status": lambda_status,
            "status": status,
            "message": message,
            **payload,
        }

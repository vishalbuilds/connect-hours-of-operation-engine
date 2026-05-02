import pytest
from common.response_builder import ResponseBuilder


class TestResponseBuilder:
    def test_open_returns_status(self):
        result = ResponseBuilder.open(status="OPEN", message="Business hours", payload={"day": "Monday"})
        assert result["status"] == "OPEN"
        assert result["message"] == "Business hours"
        assert result["payload"] == {"day": "Monday"}

    def test_closed_returns_status(self):
        result = ResponseBuilder.closed(status="CLOSED", message="Closed today", payload={"reason": "holiday"})
        assert result["status"] == "CLOSED"
        assert result["message"] == "Closed today"
        assert result["payload"] == {"reason": "holiday"}

    def test_error_returns_status(self):
        result = ResponseBuilder.error(status="ERROR", message="Bad params", payload={"code": 400})
        assert result["status"] == "ERROR"
        assert result["message"] == "Bad params"
        assert result["payload"] == {"code": 400}

    def test_open_with_no_payload_returns_empty_dict(self):
        result = ResponseBuilder.open(status="OPEN", message="Open")
        assert result["payload"] == {}

    def test_closed_with_none_payload_returns_empty_dict(self):
        result = ResponseBuilder.closed(status="CLOSED", message="Closed", payload=None)
        assert result["payload"] == {}

    def test_error_with_no_payload_returns_empty_dict(self):
        result = ResponseBuilder.error(status="ERROR", message="Error")
        assert result["payload"] == {}

    def test_build_direct_call_returns_correct_structure(self):
        result = ResponseBuilder._build("OPEN", "test message", {"k": "v"})
        assert result == {"status": "OPEN", "message": "test message", "payload": {"k": "v"}}

    def test_build_with_none_payload_returns_empty_dict(self):
        result = ResponseBuilder._build("CLOSED", "msg", None)
        assert result["payload"] == {}

    def test_holiday_status(self):
        result = ResponseBuilder.open(status="HOLIDAY", message="Public holiday")
        assert result["status"] == "HOLIDAY"

    def test_meeting_status(self):
        result = ResponseBuilder.closed(status="MEETING", message="Team meeting")
        assert result["status"] == "MEETING"

    def test_response_has_exactly_three_keys(self):
        result = ResponseBuilder.open(status="OPEN", message="msg")
        assert set(result.keys()) == {"status", "message", "payload"}

    def test_open_with_empty_payload_dict_returns_it(self):
        result = ResponseBuilder.open(status="OPEN", message="msg", payload={})
        assert result["payload"] == {}

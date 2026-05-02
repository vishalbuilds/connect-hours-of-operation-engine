import pytest
from unittest.mock import patch, MagicMock

from lambda_handler import lambda_handler


def make_event(expression_type="QUEUE", entity_id="queue-arn", time_zone="America/New_York", contact_id="contact-123"):
    return {
        "Details": {
            "ContactId": contact_id,
            "Parameters": {
                "ContactId": contact_id,
                "expression_type": expression_type,
                "id": entity_id,
                "time_zone": time_zone,
            },
        }
    }


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.aws_request_id = "test-request-id"
    ctx.function_name = "hoo-test-function"
    ctx.memory_limit_in_mb = 128
    ctx.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:hoo-test"
    return ctx


def _queue_payload(expire_date="12/31/2030"):
    return {"expireDate": expire_date, "queueName": "TestQueue"}


def _exception_payload(expire_date="12/31/2030"):
    return {"expireDate": expire_date, "description": "Holiday"}


def _schedule_payload(expire_date="12/31/2030"):
    return {"expireDate": expire_date, "startTime": "09:00", "closeTime": "18:00"}


class TestLayer1EventValidation:

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_invalid_event_returns_error(self, MockPAV, MockPS, mock_context):
        mock_pav = MockPAV.return_value
        mock_pav.get_params.return_value = {
            "contact_id": "contact-123",
            "expression_type": "",
            "id": "",
            "time_zone": "",
        }
        mock_pav.is_valid_event.return_value = False

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "ERROR"
        assert result["message"] == "Invalid event parameters"
        MockPS.assert_not_called()

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_invalid_event_payload_contains_params(self, MockPAV, MockPS, mock_context):
        params = {"contact_id": "c", "expression_type": "BAD", "id": "", "time_zone": ""}
        mock_pav = MockPAV.return_value
        mock_pav.get_params.return_value = params
        mock_pav.is_valid_event.return_value = False

        result = lambda_handler(make_event(), mock_context)

        assert result["payload"] == params


class TestLayer2QueueExpiry:

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_expired_queue_returns_closed(self, MockPAV, MockPS, mock_context):
        mock_pav = MockPAV.return_value
        mock_pav.get_params.return_value = {
            "contact_id": "c", "expression_type": "QUEUE",
            "id": "queue-arn", "time_zone": "UTC",
        }
        mock_pav.is_valid_event.return_value = True

        mock_queue_svc = MockPS.return_value
        mock_queue_svc.fetch.return_value = _queue_payload("01/01/2020")
        mock_queue_svc.check_expiry.return_value = "expired"

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "CLOSED"
        assert result["message"] == "Queue expired"

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_unknown_queue_expiry_returns_closed(self, MockPAV, MockPS, mock_context):
        mock_pav = MockPAV.return_value
        mock_pav.get_params.return_value = {
            "contact_id": "c", "expression_type": "QUEUE",
            "id": "queue-arn", "time_zone": "UTC",
        }
        mock_pav.is_valid_event.return_value = True

        mock_queue_svc = MockPS.return_value
        mock_queue_svc.fetch.return_value = {}
        mock_queue_svc.check_expiry.return_value = "unknown"

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "CLOSED"
        assert result["message"] == "Missing expiry date"


class TestLayer3ExceptionCheck:

    def _setup_valid_queue(self, MockPAV, MockPS):
        mock_pav = MockPAV.return_value
        mock_pav.get_params.return_value = {
            "contact_id": "c", "expression_type": "QUEUE",
            "id": "queue-arn", "time_zone": "UTC",
        }
        mock_pav.is_valid_event.return_value = True

        mock_queue_svc = MagicMock()
        mock_queue_svc.fetch.return_value = _queue_payload()
        mock_queue_svc.check_expiry.return_value = "valid"
        return mock_pav, mock_queue_svc

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_valid_exception_returns_open(self, MockPAV, MockPS, mock_context):
        _, mock_queue_svc = self._setup_valid_queue(MockPAV, MockPS)

        mock_exception_svc = MagicMock()
        mock_exception_svc.fetch.return_value = _exception_payload()
        mock_exception_svc.check_expiry.return_value = "valid"

        mock_queue_svc.check_payload_key_for_today.side_effect = lambda key: (
            "EXCEPTION_NEW_YEAR" if key == "EXCEPTION" else None
        )
        MockPS.side_effect = [mock_queue_svc, mock_exception_svc]

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "OPEN"
        assert result["message"] == "Exception record"

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_expired_exception_proceeds_to_schedule_check(self, MockPAV, MockPS, mock_context):
        _, mock_queue_svc = self._setup_valid_queue(MockPAV, MockPS)

        mock_exception_svc = MagicMock()
        mock_exception_svc.fetch.return_value = _exception_payload("01/01/2020")
        mock_exception_svc.check_expiry.return_value = "expired"

        mock_schedule_svc = MagicMock()
        mock_schedule_svc.fetch.return_value = _schedule_payload()
        mock_schedule_svc.check_expiry.return_value = "valid"

        mock_queue_svc.check_payload_key_for_today.side_effect = lambda key: (
            "EXCEPTION_X" if key == "EXCEPTION" else "SCHEDULE_MONDAY"
        )
        MockPS.side_effect = [mock_queue_svc, mock_exception_svc, mock_schedule_svc]

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "OPEN"
        assert result["message"] == "Schedule record"

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_unknown_exception_expiry_proceeds_to_schedule(self, MockPAV, MockPS, mock_context):
        _, mock_queue_svc = self._setup_valid_queue(MockPAV, MockPS)

        mock_exception_svc = MagicMock()
        mock_exception_svc.fetch.return_value = {}
        mock_exception_svc.check_expiry.return_value = "unknown"

        mock_schedule_svc = MagicMock()
        mock_schedule_svc.fetch.return_value = _schedule_payload()
        mock_schedule_svc.check_expiry.return_value = "valid"

        mock_queue_svc.check_payload_key_for_today.side_effect = lambda key: (
            "EXCEPTION_X" if key == "EXCEPTION" else "SCHEDULE_MONDAY"
        )
        MockPS.side_effect = [mock_queue_svc, mock_exception_svc, mock_schedule_svc]

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "OPEN"
        assert result["message"] == "Schedule record"

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_no_exception_for_today_proceeds_to_schedule(self, MockPAV, MockPS, mock_context):
        _, mock_queue_svc = self._setup_valid_queue(MockPAV, MockPS)

        mock_schedule_svc = MagicMock()
        mock_schedule_svc.fetch.return_value = _schedule_payload()
        mock_schedule_svc.check_expiry.return_value = "valid"

        mock_queue_svc.check_payload_key_for_today.side_effect = lambda key: (
            None if key == "EXCEPTION" else "SCHEDULE_MONDAY"
        )
        MockPS.side_effect = [mock_queue_svc, mock_schedule_svc]

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "OPEN"


class TestLayer4ScheduleCheck:

    def _setup_valid_queue_no_exception(self, MockPAV, MockPS):
        mock_pav = MockPAV.return_value
        mock_pav.get_params.return_value = {
            "contact_id": "c", "expression_type": "QUEUE",
            "id": "queue-arn", "time_zone": "UTC",
        }
        mock_pav.is_valid_event.return_value = True

        mock_queue_svc = MagicMock()
        mock_queue_svc.fetch.return_value = _queue_payload()
        mock_queue_svc.check_expiry.return_value = "valid"
        mock_queue_svc.check_payload_key_for_today.side_effect = lambda key: (
            None if key == "EXCEPTION" else mock_queue_svc._schedule_id
        )
        mock_queue_svc._schedule_id = "SCHEDULE_MONDAY"
        return mock_pav, mock_queue_svc

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_valid_schedule_returns_open(self, MockPAV, MockPS, mock_context):
        _, mock_queue_svc = self._setup_valid_queue_no_exception(MockPAV, MockPS)

        mock_schedule_svc = MagicMock()
        mock_schedule_svc.fetch.return_value = _schedule_payload()
        mock_schedule_svc.check_expiry.return_value = "valid"

        MockPS.side_effect = [mock_queue_svc, mock_schedule_svc]

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "OPEN"
        assert result["message"] == "Schedule record"

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_expired_schedule_returns_closed(self, MockPAV, MockPS, mock_context):
        _, mock_queue_svc = self._setup_valid_queue_no_exception(MockPAV, MockPS)

        mock_schedule_svc = MagicMock()
        mock_schedule_svc.fetch.return_value = _schedule_payload("01/01/2020")
        mock_schedule_svc.check_expiry.return_value = "expired"

        MockPS.side_effect = [mock_queue_svc, mock_schedule_svc]

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "CLOSED"
        assert result["message"] == "Schedule record expired"

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_unknown_schedule_expiry_returns_closed(self, MockPAV, MockPS, mock_context):
        _, mock_queue_svc = self._setup_valid_queue_no_exception(MockPAV, MockPS)

        mock_schedule_svc = MagicMock()
        mock_schedule_svc.fetch.return_value = {}
        mock_schedule_svc.check_expiry.return_value = "unknown"

        MockPS.side_effect = [mock_queue_svc, mock_schedule_svc]

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "CLOSED"
        assert result["message"] == "Missing schedule expiry date"

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_no_schedule_for_today_returns_closed(self, MockPAV, MockPS, mock_context):
        mock_pav = MockPAV.return_value
        mock_pav.get_params.return_value = {
            "contact_id": "c", "expression_type": "QUEUE",
            "id": "queue-arn", "time_zone": "UTC",
        }
        mock_pav.is_valid_event.return_value = True

        mock_queue_svc = MagicMock()
        mock_queue_svc.fetch.return_value = _queue_payload()
        mock_queue_svc.check_expiry.return_value = "valid"
        mock_queue_svc.check_payload_key_for_today.return_value = None

        MockPS.side_effect = [mock_queue_svc]

        result = lambda_handler(make_event(), mock_context)

        assert result["status"] == "CLOSED"
        assert result["message"] == "No schedule found for today"
        assert result["payload"] == _queue_payload()

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_no_schedule_payload_is_queue_payload(self, MockPAV, MockPS, mock_context):
        mock_pav = MockPAV.return_value
        queue_payload = _queue_payload()
        mock_pav.get_params.return_value = {
            "contact_id": "c", "expression_type": "QUEUE",
            "id": "queue-arn", "time_zone": "UTC",
        }
        mock_pav.is_valid_event.return_value = True

        mock_queue_svc = MagicMock()
        mock_queue_svc.fetch.return_value = queue_payload
        mock_queue_svc.check_expiry.return_value = "valid"
        mock_queue_svc.check_payload_key_for_today.return_value = None

        MockPS.side_effect = [mock_queue_svc]

        result = lambda_handler(make_event(), mock_context)

        assert result["payload"] == queue_payload


class TestPayloadServiceInstantiation:

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_queue_service_created_with_correct_args(self, MockPAV, MockPS, mock_context):
        mock_pav = MockPAV.return_value
        mock_pav.get_params.return_value = {
            "contact_id": "c", "expression_type": "QUEUE",
            "id": "test-queue-arn", "time_zone": "Asia/Kolkata",
        }
        mock_pav.is_valid_event.return_value = True

        mock_queue_svc = MagicMock()
        mock_queue_svc.fetch.return_value = _queue_payload()
        mock_queue_svc.check_expiry.return_value = "valid"
        mock_queue_svc.check_payload_key_for_today.return_value = None
        MockPS.side_effect = [mock_queue_svc]

        lambda_handler(make_event(), mock_context)

        MockPS.assert_called_once_with("QUEUE", "test-queue-arn", "Asia/Kolkata")

    @patch("lambda_handler.PayloadService")
    @patch("lambda_handler.ParseAndValidate")
    def test_exception_service_created_with_correct_args(self, MockPAV, MockPS, mock_context):
        mock_pav = MockPAV.return_value
        mock_pav.get_params.return_value = {
            "contact_id": "c", "expression_type": "QUEUE",
            "id": "queue-arn", "time_zone": "UTC",
        }
        mock_pav.is_valid_event.return_value = True

        mock_queue_svc = MagicMock()
        mock_queue_svc.fetch.return_value = _queue_payload()
        mock_queue_svc.check_expiry.return_value = "valid"
        mock_queue_svc.check_payload_key_for_today.side_effect = lambda key: (
            "EXCEPTION_X" if key == "EXCEPTION" else None
        )

        mock_exception_svc = MagicMock()
        mock_exception_svc.fetch.return_value = _exception_payload()
        mock_exception_svc.check_expiry.return_value = "valid"

        MockPS.side_effect = [mock_queue_svc, mock_exception_svc]

        lambda_handler(make_event(), mock_context)

        assert MockPS.call_args_list[1][0] == ("EXCEPTION", "EXCEPTION_X", "UTC")

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock

from common.payload_service import PayloadService


TZ = "UTC"
FUTURE_DATE = "12/31/2030"
PAST_DATE = "01/01/2020"


def make_service(pk="QUEUE", sk="queue-id", time_zone=TZ):
    return PayloadService(pk, sk, time_zone)


class TestPayloadServiceConstructor:

    def test_pk_prefixed_with_exp_queue(self):
        svc = make_service(pk="QUEUE")
        assert svc.pk == "EXP#QUEUE"

    def test_pk_prefixed_with_exp_exception(self):
        svc = make_service(pk="EXCEPTION")
        assert svc.pk == "EXP#EXCEPTION"

    def test_pk_prefixed_with_exp_schedule(self):
        svc = make_service(pk="SCHEDULE")
        assert svc.pk == "EXP#SCHEDULE"

    def test_pk_prefixed_with_exp_phone_number(self):
        svc = make_service(pk="PHONE_NUMBER")
        assert svc.pk == "EXP#PHONE_NUMBER"

    def test_sk_stored(self):
        svc = make_service(sk="some-sk-value")
        assert svc.sk == "some-sk-value"

    def test_payload_initially_none(self):
        svc = make_service()
        assert svc.payload is None

    def test_date_time_now_is_timezone_aware(self):
        svc = make_service(time_zone="America/New_York")
        assert svc.date_time_now.tzinfo is not None

    def test_different_timezones_produce_different_offsets(self):
        utc_svc = make_service(time_zone="UTC")
        kolkata_svc = make_service(time_zone="Asia/Kolkata")
        assert utc_svc.date_time_now.utcoffset() != kolkata_svc.date_time_now.utcoffset()


class TestFetch:

    @patch("common.payload_service.get_item")
    def test_fetch_returns_item_and_sets_payload(self, mock_get_item):
        item = {"expireDate": FUTURE_DATE, "queueName": "TestQueue"}
        mock_get_item.return_value = item

        svc = make_service()
        result = svc.fetch()

        assert result == item
        assert svc.payload == item

    @patch("common.payload_service.get_item")
    def test_fetch_returns_none_when_not_found(self, mock_get_item):
        mock_get_item.return_value = None

        svc = make_service()
        result = svc.fetch()

        assert result is None
        assert svc.payload is None

    @patch("common.payload_service.get_item")
    def test_fetch_calls_get_item_with_correct_args(self, mock_get_item):
        mock_get_item.return_value = None

        svc = make_service(pk="EXCEPTION", sk="EXCEPTION_NEW_YEAR")
        svc.fetch()

        mock_get_item.assert_called_once_with("EXP#EXCEPTION", "EXCEPTION_NEW_YEAR")


class TestCheckExpiry:

    def test_unknown_when_payload_is_none(self):
        svc = make_service()
        svc.payload = None
        assert svc.check_expiry() == "unknown"

    def test_unknown_when_payload_is_empty_dict(self):
        svc = make_service()
        svc.payload = {}
        assert svc.check_expiry() == "unknown"

    def test_unknown_when_expire_date_field_missing(self):
        svc = make_service()
        svc.payload = {"name": "SomeSchedule"}
        assert svc.check_expiry() == "unknown"

    def test_unknown_when_expire_date_is_none(self):
        svc = make_service()
        svc.payload = {"expireDate": None}
        assert svc.check_expiry() == "unknown"

    def test_valid_when_expire_date_is_future(self):
        svc = make_service()
        svc.payload = {"expireDate": FUTURE_DATE}
        assert svc.check_expiry() == "valid"

    def test_expired_when_expire_date_is_past(self):
        svc = make_service()
        svc.payload = {"expireDate": PAST_DATE}
        assert svc.check_expiry() == "expired"

    def test_valid_when_expire_date_equals_today(self):
        fixed_now = datetime(2026, 4, 28, 12, 0, tzinfo=ZoneInfo(TZ))
        with patch("common.payload_service.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.strptime = datetime.strptime
            svc = make_service()

        svc.payload = {"expireDate": "04/28/2026"}
        assert svc.check_expiry() == "valid"

    def test_expired_when_today_is_one_day_after_expiry(self):
        fixed_now = datetime(2026, 4, 29, 0, 0, tzinfo=ZoneInfo(TZ))
        with patch("common.payload_service.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.strptime = datetime.strptime
            svc = make_service()

        svc.payload = {"expireDate": "04/28/2026"}
        assert svc.check_expiry() == "expired"


class TestCheckPayloadKeyForToday:

    @patch("common.payload_service.get_item")
    def test_exception_key_found(self, mock_get_item):
        svc = make_service()
        today_str = svc.date_time_now.strftime("%m/%d/%Y")
        mock_get_item.return_value = {f"EXCEPTION#{today_str}": "EXCEPTION_NEW_YEAR"}
        svc.fetch()

        result = svc.check_payload_key_for_today("EXCEPTION")

        assert result == "EXCEPTION_NEW_YEAR"

    @patch("common.payload_service.get_item")
    def test_exception_key_not_found_returns_none(self, mock_get_item):
        mock_get_item.return_value = {"unrelated_key": "value"}
        svc = make_service()
        svc.fetch()

        result = svc.check_payload_key_for_today("EXCEPTION")

        assert result is None

    @patch("common.payload_service.get_item")
    def test_schedule_key_found(self, mock_get_item):
        svc = make_service()
        today_day = svc.date_time_now.strftime("%A")
        mock_get_item.return_value = {f"SCHEDULE#{today_day}": "SCHEDULE_MONDAY"}
        svc.fetch()

        result = svc.check_payload_key_for_today("SCHEDULE")

        assert result == "SCHEDULE_MONDAY"

    @patch("common.payload_service.get_item")
    def test_schedule_key_not_found_returns_none(self, mock_get_item):
        mock_get_item.return_value = {"unrelated_key": "value"}
        svc = make_service()
        svc.fetch()

        result = svc.check_payload_key_for_today("SCHEDULE")

        assert result is None

    def test_invalid_key_type_raises_value_error(self):
        svc = make_service()
        svc.payload = {"some": "data"}

        with pytest.raises(ValueError, match="Invalid key type"):
            svc.check_payload_key_for_today("INVALID")

    @patch("common.payload_service.get_item")
    def test_returns_none_when_payload_is_none(self, mock_get_item):
        mock_get_item.return_value = None
        svc = make_service()
        svc.fetch()

        result = svc.check_payload_key_for_today("EXCEPTION")

        assert result is None

    @patch("common.payload_service.get_item")
    def test_schedule_returns_none_when_payload_is_none(self, mock_get_item):
        mock_get_item.return_value = None
        svc = make_service()
        svc.fetch()

        result = svc.check_payload_key_for_today("SCHEDULE")

        assert result is None

    @patch("common.payload_service.get_item")
    def test_exception_key_uses_date_format(self, mock_get_item):
        fixed_now = datetime(2026, 1, 1, 10, 0, tzinfo=ZoneInfo(TZ))
        with patch("common.payload_service.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.strptime = datetime.strptime
            svc = make_service()

        mock_get_item.return_value = {"EXCEPTION#01/01/2026": "EXCEPTION_NEW_YEAR"}
        svc.fetch()
        result = svc.check_payload_key_for_today("EXCEPTION")

        assert result == "EXCEPTION_NEW_YEAR"

    @patch("common.payload_service.get_item")
    def test_schedule_key_uses_full_day_name(self, mock_get_item):
        fixed_now = datetime(2026, 4, 27, 10, 0, tzinfo=ZoneInfo(TZ))  # Monday
        with patch("common.payload_service.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.strptime = datetime.strptime
            svc = make_service()

        mock_get_item.return_value = {"SCHEDULE#Monday": "SCHEDULE_MONDAY"}
        svc.fetch()
        result = svc.check_payload_key_for_today("SCHEDULE")

        assert result == "SCHEDULE_MONDAY"

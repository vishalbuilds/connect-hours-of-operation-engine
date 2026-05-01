import pytest
from common.parse_and_validate import ParseAndValidate


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


class TestParseAndValidate:

    # --- constructor / get_params ---

    def test_get_params_returns_correct_keys(self):
        pav = ParseAndValidate(make_event())
        params = pav.get_params()
        assert set(params.keys()) == {"expression_type", "id", "time_zone", "contact_id"}

    def test_expression_type_uppercased(self):
        pav = ParseAndValidate(make_event(expression_type="queue"))
        assert pav.get_params()["expression_type"] == "QUEUE"

    def test_expression_type_stripped(self):
        pav = ParseAndValidate(make_event(expression_type="  QUEUE  "))
        assert pav.get_params()["expression_type"] == "QUEUE"

    def test_id_stripped(self):
        pav = ParseAndValidate(make_event(entity_id="  some-arn  "))
        assert pav.get_params()["id"] == "some-arn"

    def test_time_zone_stripped(self):
        pav = ParseAndValidate(make_event(time_zone="  UTC  "))
        assert pav.get_params()["time_zone"] == "UTC"

    def test_contact_id_extracted(self):
        pav = ParseAndValidate(make_event(contact_id="test-contact"))
        assert pav.get_params()["contact_id"] == "test-contact"

    def test_missing_contact_id_defaults_to_unknown(self):
        event = {"Details": {"Parameters": {"expression_type": "QUEUE", "id": "x", "time_zone": "UTC"}}}
        pav = ParseAndValidate(event)
        assert pav.get_params()["contact_id"] == "UNKNOWN"

    def test_empty_event_sets_empty_fields(self):
        pav = ParseAndValidate({})
        params = pav.get_params()
        assert params["expression_type"] == ""
        assert params["id"] == ""
        assert params["time_zone"] == ""
        assert params["contact_id"] == "UNKNOWN"

    def test_missing_details_key_sets_defaults(self):
        pav = ParseAndValidate({"Other": {}})
        params = pav.get_params()
        assert params["expression_type"] == ""

    # --- is_valid_event: VALID paths ---

    def test_valid_queue_event(self):
        pav = ParseAndValidate(make_event(expression_type="QUEUE"))
        assert pav.is_valid_event() is True

    def test_valid_phone_number_event(self):
        pav = ParseAndValidate(make_event(expression_type="PHONE_NUMBER"))
        assert pav.is_valid_event() is True

    def test_valid_lowercase_expression_type_accepted(self):
        pav = ParseAndValidate(make_event(expression_type="queue"))
        assert pav.is_valid_event() is True

    def test_valid_utc_timezone(self):
        pav = ParseAndValidate(make_event(time_zone="UTC"))
        assert pav.is_valid_event() is True

    # --- is_valid_event: INVALID paths ---

    def test_missing_expression_type_is_invalid(self):
        pav = ParseAndValidate(make_event(expression_type=""))
        assert pav.is_valid_event() is False

    def test_missing_id_is_invalid(self):
        pav = ParseAndValidate(make_event(entity_id=""))
        assert pav.is_valid_event() is False

    def test_missing_time_zone_is_invalid(self):
        pav = ParseAndValidate(make_event(time_zone=""))
        assert pav.is_valid_event() is False

    def test_unsupported_expression_type_is_invalid(self):
        pav = ParseAndValidate(make_event(expression_type="EXCEPTION"))
        assert pav.is_valid_event() is False

    def test_arbitrary_expression_type_is_invalid(self):
        pav = ParseAndValidate(make_event(expression_type="SCHEDULE"))
        assert pav.is_valid_event() is False

    def test_invalid_timezone_is_invalid(self):
        pav = ParseAndValidate(make_event(time_zone="Not/AReal/Zone"))
        assert pav.is_valid_event() is False

    def test_empty_event_is_invalid(self):
        pav = ParseAndValidate({})
        assert pav.is_valid_event() is False

    def test_whitespace_only_id_is_invalid(self):
        pav = ParseAndValidate(make_event(entity_id="   "))
        assert pav.is_valid_event() is False

    def test_whitespace_only_expression_type_is_invalid(self):
        pav = ParseAndValidate(make_event(expression_type="   "))
        assert pav.is_valid_event() is False

from typing import Any, Dict

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from common.payload_service import PayloadService
from common.parse_and_validate import ParseAndValidate
from common.response_builder import ResponseBuilder

logger = Logger(service="hours-of-operation")


@logger.inject_lambda_context(clear_state=True, log_event=False)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:

    # ------------------------------------------------------------------
    # Layer 1 — event validation
    # ------------------------------------------------------------------

    parse_and_validate_obj = ParseAndValidate(event)
    parameters = parse_and_validate_obj.get_params()
    logger.append_keys(
        ContactId=parameters["contact_id"] or event["Details"]["ContactId"]
    )

    if not parse_and_validate_obj.is_valid_event():
        return ResponseBuilder.error(
            status="ERROR", message="Invalid event parameters", payload=parameters
        )

    # ------------------------------------------------------------------
    # Layer 2 — Queue / entity configuration
    # ------------------------------------------------------------------

    queue_svc_obj = PayloadService(
        parameters["expression_type"], parameters["id"], parameters["time_zone"]
    )
    queue_payload = queue_svc_obj.fetch()
    queue_expiry = queue_svc_obj.check_expiry()

    if queue_expiry == "expired":
        return ResponseBuilder.closed(
            status="CLOSED", message="Queue expired", payload=queue_payload
        )
    if queue_expiry == "unknown":
        return ResponseBuilder.closed(
            status="CLOSED", message="Missing expiry date", payload=queue_payload
        )

    # ------------------------------------------------------------------
    # Layer 3 — Exception check (overrides schedule when valid)
    # ------------------------------------------------------------------

    exception_id = queue_svc_obj.check_payload_key_for_today("EXCEPTION")
    if exception_id:
        exception_svc_obj = PayloadService(
            "EXCEPTION", exception_id, parameters["time_zone"]
        )
        exception_payload = exception_svc_obj.fetch()
        exception_expiry = exception_svc_obj.check_expiry()

        if exception_expiry == "valid":
            return ResponseBuilder.open(
                status="OPEN", message="Exception record", payload=exception_payload
            )
        if exception_expiry == "expired":
            logger.info(
                "Exception record expired, proceeding to schedule check",
                extra={"exception_id": exception_id},
            )
        if exception_expiry == "unknown":
            logger.info(
                "Exception record missing expiry date, proceeding to schedule check",
                extra={"exception_id": exception_id},
            )

    # ------------------------------------------------------------------
    # Layer 4 — Schedule check
    # ------------------------------------------------------------------

    schedule_id = queue_svc_obj.check_payload_key_for_today("SCHEDULE")
    if schedule_id:
        schedule_svc_obj = PayloadService(
            "SCHEDULE", schedule_id, parameters["time_zone"]
        )
        schedule_payload = schedule_svc_obj.fetch()
        schedule_expiry = schedule_svc_obj.check_expiry()

        if schedule_expiry == "valid":
            return ResponseBuilder.open(
                status="OPEN", message="Schedule record", payload=schedule_payload
            )
        if schedule_expiry == "expired":
            return ResponseBuilder.closed(
                status="CLOSED",
                message="Schedule record expired",
                payload=schedule_payload,
            )
        if schedule_expiry == "unknown":
            return ResponseBuilder.closed(
                status="CLOSED",
                message="Missing schedule expiry date",
                payload=schedule_payload,
            )

    return ResponseBuilder.closed(
        status="CLOSED", message="No schedule found for today", payload=queue_payload
    )

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aws_lambda_powertools import Logger

logger = Logger(child=True)

HOO_PK_MAP: list[str] = ["QUEUE", "PHONE_NUMBER"]


class ParseAndValidate:
    def __init__(self, event):

        params = event.get("Details", {}).get("Parameters", {})

        self.contact_id: str = params.get("ContactId", "UNKNOWN")
        self.expression_pk: str = params.get("expression_type", "").strip().upper()
        self.id_sk: str = params.get("id", "").strip()
        self.time_zone: str = params.get("time_zone", "").strip()

    def is_valid_event(self):
        if not self.expression_pk or not self.id_sk or not self.time_zone:
            logger.error(
                "Missing required event parameters",
                extra={
                    "expression_type": self.expression_pk,
                    "entity_id": self.id_sk,
                },
            )
            return False
        if self.expression_pk not in HOO_PK_MAP:
            logger.error(
                "Unsupported expression_type",
                extra={"expression_type": self.expression_pk, "supported": HOO_PK_MAP},
            )
            return False
        try:
            ZoneInfo(self.time_zone)
        except ZoneInfoNotFoundError:
            logger.error(
                "Invalid time_zone parameter",
                extra={"time_zone": self.time_zone},
            )
            return False
        return True

    def get_params(self):
        return {
            "expression_type": self.expression_pk,
            "id": self.id_sk,
            "time_zone": self.time_zone,
            "contact_id": self.contact_id,
        }

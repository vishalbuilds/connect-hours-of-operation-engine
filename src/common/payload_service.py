from typing import Dict, Optional, Literal
from datetime import datetime
from zoneinfo import ZoneInfo

from aws_lambda_powertools import Logger
from common.dynamodb import get_item

logger = Logger(child=True)

_DATE_FMT = "%m/%d/%Y"


class PayloadService:

    def __init__(
        self,
        pk: Literal["EXCEPTION", "SCHEDULE", "QUEUE", "PHONE_NUMBER"],
        sk: str,
        time_zone: str,
    ) -> None:
        self.pk = f"EXP#{pk}"
        self.sk = sk
        self.date_time_now = datetime.now(ZoneInfo(time_zone))
        self.payload = None

    def fetch(self) -> Optional[Dict]:
        """Fetch the record from DynamoDB.

        Returns:
            The raw DynamoDB item dict, or ``None`` if the record does not exist.
        """
        response = get_item(self.pk, self.sk)
        if response:
            logger.info(
                "HOO record fetched successfully",
                extra={
                    "pk": self.pk,
                    "sk": self.sk,
                    **response,
                },
            )
        else:
            logger.error(
                "HOO record not found",
                extra={
                    "pk": self.pk,
                    "sk": self.sk,
                },
            )
        self.payload = response
        return response

    def check_expiry(self) -> str:

        if not self.payload:
            return "unknown"

        expiry_date_str = self.payload.get("expireDate")
        if not expiry_date_str:
            return "unknown"

        today = self.date_time_now.date()
        expiry_date = datetime.strptime(expiry_date_str, _DATE_FMT).date()

        if today > expiry_date:
            return "expired"
        else:
            return "valid"

    def check_payload_key_for_today(
        self, key_type: Literal["EXCEPTION", "SCHEDULE"]
    ) -> Optional[str]:
        if key_type == "EXCEPTION":
            today = self.date_time_now.strftime(_DATE_FMT)
        elif key_type == "SCHEDULE":
            today = self.date_time_now.strftime("%A")
        else:
            raise ValueError("Invalid key type")

        if not self.payload:
            return None

        key = f"{key_type}#{today}"
        value = self.payload.get(key)
        if value:
            return value
        return None

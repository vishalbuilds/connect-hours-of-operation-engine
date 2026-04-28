import os
from typing import Any, Dict, Optional

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import BotoCoreError, ClientError

logger = Logger(child=True)

REGION = os.environ.get("AWS_REGION", "us-west-2")
TABLE_NAME = os.environ["TABLE_NAME"]


def get_item(pk_value: str, sk_value: str) -> Optional[Dict[str, Any]]:
    try:
        response = (
            boto3.resource("dynamodb", region_name=REGION)
            .Table(TABLE_NAME)
            .get_item(Key={"exp": pk_value, "id": sk_value})
        )
        return response.get("Item")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(
            "DynamoDB ClientError",
            extra={
                "error_code": error_code,
                "error_message": error_message,
                "pk": pk_value,
                "sk": sk_value,
            },
        )
        raise
    except BotoCoreError as e:
        logger.error(
            "DynamoDB BotoCoreError",
            extra={"error": str(e), "pk": pk_value, "sk": sk_value},
        )
        raise

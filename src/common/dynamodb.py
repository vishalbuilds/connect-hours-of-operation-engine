import os
from typing import Any, Dict, Optional

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import BotoCoreError, ClientError

logger = Logger(child=True)

_table = None


def _get_table():
    global _table
    if _table is None:
        region = os.environ.get("AWS_REGION", "us-west-2")
        table_name = os.environ["TABLE_NAME"]
        _table = boto3.resource("dynamodb", region_name=region).Table(table_name)
    return _table


def get_item(pk_value: str, sk_value: str) -> Optional[Dict[str, Any]]:
    pk_name = os.environ.get("PK_NAME", "pk")
    sk_name = os.environ.get("SK_NAME", "sk")
    try:
        response = _get_table().get_item(Key={pk_name: pk_value, sk_name: sk_value})
        return response.get("Item")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(
            "DynamoDB ClientError",
            extra={"error_code": error_code, "error_message": error_message, "pk": pk_value, "sk": sk_value},
        )
        raise
    except BotoCoreError as e:
        logger.error(
            "DynamoDB BotoCoreError",
            extra={"error": str(e), "pk": pk_value, "sk": sk_value},
        )
        raise

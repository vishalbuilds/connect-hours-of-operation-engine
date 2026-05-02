import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, BotoCoreError

import common.dynamodb as dynamodb_module
from common.dynamodb import get_item


def _client_error(code="ValidationException", message="Test error"):
    return ClientError({"Error": {"Code": code, "Message": message}}, "GetItem")


class TestGetTable:

    @patch("common.dynamodb.boto3")
    def test_creates_table_with_env_region(self, mock_boto3):
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        result = dynamodb_module._get_table()

        mock_boto3.resource.assert_called_once_with("dynamodb", region_name="us-east-1")
        mock_boto3.resource.return_value.Table.assert_called_once_with("test-hoo-table")
        assert result is mock_table

    @patch("common.dynamodb.boto3")
    def test_default_region_when_env_not_set(self, mock_boto3, monkeypatch):
        monkeypatch.delenv("AWS_REGION", raising=False)
        mock_boto3.resource.return_value.Table.return_value = MagicMock()

        dynamodb_module._get_table()

        mock_boto3.resource.assert_called_once_with("dynamodb", region_name="us-west-2")

    @patch("common.dynamodb.boto3")
    def test_singleton_only_creates_table_once(self, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = MagicMock()

        t1 = dynamodb_module._get_table()
        t2 = dynamodb_module._get_table()

        assert t1 is t2
        mock_boto3.resource.assert_called_once()

    @patch("common.dynamodb.boto3")
    def test_uses_table_name_from_env(self, mock_boto3, monkeypatch):
        monkeypatch.setenv("TABLE_NAME", "custom-table")
        mock_boto3.resource.return_value.Table.return_value = MagicMock()

        dynamodb_module._get_table()

        mock_boto3.resource.return_value.Table.assert_called_once_with("custom-table")


class TestGetItem:

    @patch("common.dynamodb._get_table")
    def test_returns_item_when_found(self, mock_get_table):
        item = {"pk": "EXP#QUEUE", "sk": "queue-arn", "expireDate": "12/31/2027"}
        mock_get_table.return_value.get_item.return_value = {"Item": item}

        result = get_item("EXP#QUEUE", "queue-arn")

        assert result == item

    @patch("common.dynamodb._get_table")
    def test_returns_none_when_item_not_found(self, mock_get_table):
        mock_get_table.return_value.get_item.return_value = {}

        result = get_item("EXP#QUEUE", "missing-id")

        assert result is None

    @patch("common.dynamodb._get_table")
    def test_uses_default_pk_sk_names(self, mock_get_table):
        mock_get_table.return_value.get_item.return_value = {}

        get_item("pk-val", "sk-val")

        mock_get_table.return_value.get_item.assert_called_once_with(
            Key={"pk": "pk-val", "sk": "sk-val"}
        )

    @patch("common.dynamodb._get_table")
    def test_uses_custom_pk_sk_names_from_env(self, mock_get_table, monkeypatch):
        monkeypatch.setenv("PK_NAME", "exp")
        monkeypatch.setenv("SK_NAME", "id")
        mock_get_table.return_value.get_item.return_value = {}

        get_item("pk-val", "sk-val")

        mock_get_table.return_value.get_item.assert_called_once_with(
            Key={"exp": "pk-val", "id": "sk-val"}
        )

    @patch("common.dynamodb._get_table")
    def test_raises_client_error(self, mock_get_table):
        mock_get_table.return_value.get_item.side_effect = _client_error(
            code="ResourceNotFoundException", message="Table not found"
        )

        with pytest.raises(ClientError):
            get_item("pk", "sk")

    @patch("common.dynamodb._get_table")
    def test_raises_botocore_error(self, mock_get_table):
        mock_get_table.return_value.get_item.side_effect = BotoCoreError()

        with pytest.raises(BotoCoreError):
            get_item("pk", "sk")

    @patch("common.dynamodb._get_table")
    def test_passes_pk_and_sk_values_correctly(self, mock_get_table):
        mock_get_table.return_value.get_item.return_value = {"Item": {"data": "x"}}

        result = get_item("EXP#EXCEPTION", "EXCEPTION_NEW_YEAR")

        mock_get_table.return_value.get_item.assert_called_once_with(
            Key={"pk": "EXP#EXCEPTION", "sk": "EXCEPTION_NEW_YEAR"}
        )
        assert result == {"data": "x"}

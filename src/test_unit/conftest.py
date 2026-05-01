import pytest


@pytest.fixture(autouse=True)
def aws_env_vars(monkeypatch):
    monkeypatch.setenv("TABLE_NAME", "test-hoo-table")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("PK_NAME", "pk")
    monkeypatch.setenv("SK_NAME", "sk")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "hours-of-operation-test")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")


@pytest.fixture(autouse=True)
def reset_dynamodb_singleton():
    import common.dynamodb as ddb
    ddb._table = None
    yield
    ddb._table = None

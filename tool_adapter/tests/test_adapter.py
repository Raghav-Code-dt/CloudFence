import json
from io import BytesIO
import pytest

import adapter as adapter_module
from adapter import (
    CloudFenceToolAdapter,
    LAMBDA_CONNECT_TIMEOUT_SECONDS,
    LAMBDA_MAX_ATTEMPTS,
    LAMBDA_READ_TIMEOUT_SECONDS,
    ToolInputError,
    ToolInvocationError,
)
from config import FUNCTIONS, APPROVED_INSTANCE_ID

class FakePayload:
    def __init__(self, value):
        self.value = value
    def read(self):
        return json.dumps(self.value).encode()

class FakeLambda:
    def __init__(self, response=None, exception=None):
        self.response = response or {"statusCode": 200, "body": json.dumps({"state": "stopped"})}
        self.exception = exception
        self.calls = []
    def invoke(self, **kwargs):
        self.calls.append(kwargs)
        if self.exception:
            raise self.exception
        return {"Payload": FakePayload(self.response)}

def test_fixed_function_mapping_and_success():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    result = adapter.invoke("get_instance_metadata", {"instance_id": APPROVED_INSTANCE_ID})
    assert result["ok"] is True
    assert client.calls[0]["FunctionName"] == FUNCTIONS["get_instance_metadata"]

def test_rejects_unknown_tool_before_invocation():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError):
        adapter.invoke("arbitrary_lambda", {})
    assert client.calls == []

def test_rejects_unapproved_instance_before_invocation():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError):
        adapter.invoke("get_instance_metadata", {"instance_id": "i-000000000000000"})
    assert client.calls == []

def test_rejects_extra_parameters():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError):
        adapter.invoke("get_approved_logs", {"log_group": "/other/group"})
    assert client.calls == []

def test_rejects_missing_required_parameter():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError):
        adapter.invoke("get_cpu_metrics", {})
    assert client.calls == []

def test_lambda_error_payload_is_not_reported_as_success():
    client = FakeLambda({"statusCode": 403, "body": json.dumps({"error": "Instance not authorized"})})
    adapter = CloudFenceToolAdapter(client)
    result = adapter.invoke("get_instance_metadata", {"instance_id": APPROVED_INSTANCE_ID})
    assert result["ok"] is False
    assert result["status_code"] == 403

def test_invocation_exception_is_wrapped():
    client = FakeLambda(exception=RuntimeError("sensitive underlying detail"))
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInvocationError):
        adapter.invoke("get_approved_logs", {})

# Timestamp validation tests

def test_rejects_empty_timestamp():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError, match="must not be empty or whitespace"):
        adapter.invoke("get_cpu_metrics", {"instance_id": APPROVED_INSTANCE_ID, "start_time": ""})
    assert client.calls == []

def test_rejects_whitespace_timestamp():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError, match="must not be empty or whitespace"):
        adapter.invoke("get_approved_logs", {"end_time": "   \t\n  "})
    assert client.calls == []

def test_rejects_malformed_timestamp():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError, match="must be a valid ISO-8601 timestamp"):
        adapter.invoke("get_cpu_metrics", {"instance_id": APPROVED_INSTANCE_ID, "start_time": "not-a-timestamp"})
    assert client.calls == []

def test_rejects_timestamp_without_timezone():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError, match="must include a timezone offset"):
        adapter.invoke("get_cpu_metrics", {"instance_id": APPROVED_INSTANCE_ID, "start_time": "2026-11-24T12:00:00"})
    assert client.calls == []

def test_rejects_reversed_timestamps():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError, match="start_time must be strictly before end_time"):
        adapter.invoke("get_cpu_metrics", {
            "instance_id": APPROVED_INSTANCE_ID,
            "start_time": "2026-11-24T12:00:00Z",
            "end_time": "2026-11-24T11:00:00Z",
        })
    assert client.calls == []

def test_rejects_equal_timestamps():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError, match="start_time must be strictly before end_time"):
        adapter.invoke("get_approved_logs", {
            "start_time": "2026-11-24T12:00:00Z",
            "end_time": "2026-11-24T12:00:00Z",
        })
    assert client.calls == []

def test_rejects_future_end_timestamp():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError, match="end_time cannot be in the future"):
        adapter.invoke("get_approved_logs", {
            "end_time": "2099-01-01T00:00:00Z",
        })
    assert client.calls == []

def test_rejects_range_exceeding_one_hour():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    with pytest.raises(ToolInputError, match="Query time window cannot exceed one hour"):
        adapter.invoke("get_cpu_metrics", {
            "instance_id": APPROVED_INSTANCE_ID,
            "start_time": "2026-11-20T10:00:00Z",
            "end_time": "2026-11-20T11:30:00Z",
        })
    assert client.calls == []

def test_accepts_valid_timestamps_with_different_timezone_offsets():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    # start: 09:15 UTC
    # end: 15:00 +05:30 (which is 09:30 UTC)
    # window is 15 minutes, strictly positive and <= 1 hour
    result = adapter.invoke("get_cpu_metrics", {
        "instance_id": APPROVED_INSTANCE_ID,
        "start_time": "2026-11-20T09:15:00Z",
        "end_time": "2026-11-20T15:00:00+05:30",
    })
    assert result["ok"] is True
    assert len(client.calls) == 1

def test_accepts_valid_range_within_limit_and_invokes_lambda():
    client = FakeLambda()
    adapter = CloudFenceToolAdapter(client)
    # 09:45 UTC to 15:30+05:30 (10:00 UTC) = 15 minute window
    result = adapter.invoke("get_cpu_metrics", {
        "instance_id": APPROVED_INSTANCE_ID,
        "start_time": "2026-11-20T09:45:00Z",
        "end_time": "2026-11-20T15:30:00+05:30",
    })
    assert result["ok"] is True
    assert len(client.calls) == 1
    call_payload = json.loads(client.calls[0]["Payload"].decode())
    assert call_payload["start_time"] == "2026-11-20T09:45:00Z"
    assert call_payload["end_time"] == "2026-11-20T15:30:00+05:30"

# Resiliency, timeout, and error-handling tests

def test_default_boto3_client_uses_explicit_timeout_and_retry_config(monkeypatch):
    captured = {}

    class FakeConfig:
        def __init__(self, **kwargs):
            captured["config_kwargs"] = kwargs

    class FakeBoto3:
        @staticmethod
        def client(service_name, config=None):
            captured["service_name"] = service_name
            captured["config"] = config
            return FakeLambda()

    monkeypatch.setattr(adapter_module, "Config", FakeConfig)
    monkeypatch.setattr(adapter_module, "boto3", FakeBoto3)

    CloudFenceToolAdapter()
    assert captured["service_name"] == "lambda"
    assert captured["config_kwargs"] == {
        "connect_timeout": LAMBDA_CONNECT_TIMEOUT_SECONDS,
        "read_timeout": LAMBDA_READ_TIMEOUT_SECONDS,
        "retries": {"max_attempts": LAMBDA_MAX_ATTEMPTS},
    }
    assert LAMBDA_CONNECT_TIMEOUT_SECONDS == 3
    assert LAMBDA_READ_TIMEOUT_SECONDS == 10
    assert LAMBDA_MAX_ATTEMPTS == 1

def test_connect_timeout_raises_tool_invocation_error(monkeypatch):
    class FakeConnectTimeoutError(Exception):
        pass

    monkeypatch.setattr(adapter_module, "ConnectTimeoutError", FakeConnectTimeoutError)
    client = FakeLambda(exception=FakeConnectTimeoutError("connect timed out to 10.0.0.1"))
    adapter = CloudFenceToolAdapter(client)

    with pytest.raises(ToolInvocationError, match="timed out during connection") as exc_info:
        adapter.invoke("get_approved_logs", {})
    assert "10.0.0.1" not in str(exc_info.value)

def test_read_timeout_raises_tool_invocation_error(monkeypatch):
    class FakeReadTimeoutError(Exception):
        pass

    monkeypatch.setattr(adapter_module, "ReadTimeoutError", FakeReadTimeoutError)
    client = FakeLambda(exception=FakeReadTimeoutError("read timed out on internal socket"))
    adapter = CloudFenceToolAdapter(client)

    with pytest.raises(ToolInvocationError, match="timed out waiting for response") as exc_info:
        adapter.invoke("get_approved_logs", {})
    assert "internal socket" not in str(exc_info.value)

def test_connection_network_failure_raises_tool_invocation_error(monkeypatch):
    class FakeEndpointConnectionError(Exception):
        pass

    monkeypatch.setattr(adapter_module, "EndpointConnectionError", FakeEndpointConnectionError)
    client = FakeLambda(exception=FakeEndpointConnectionError("Could not connect to endpoint"))
    adapter = CloudFenceToolAdapter(client)

    with pytest.raises(ToolInvocationError, match="connection error"):
        adapter.invoke("get_approved_logs", {})

def test_builtin_connection_error_raises_tool_invocation_error():
    client = FakeLambda(exception=ConnectionError("network unreachable"))
    adapter = CloudFenceToolAdapter(client)

    with pytest.raises(ToolInvocationError, match="connection error"):
        adapter.invoke("get_approved_logs", {})

def test_aws_client_error_raises_tool_invocation_error_without_leaking_details(monkeypatch):
    class FakeClientError(Exception):
        def __init__(self, response):
            self.response = response

    monkeypatch.setattr(adapter_module, "ClientError", FakeClientError)
    client = FakeLambda(
        exception=FakeClientError({
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "User arn:aws:iam::123456789012:role/secret-role is not authorized",
            }
        })
    )
    adapter = CloudFenceToolAdapter(client)

    with pytest.raises(ToolInvocationError, match="AWS ClientError \\(AccessDeniedException\\)") as exc_info:
        adapter.invoke("get_approved_logs", {})
    assert "123456789012" not in str(exc_info.value)
    assert "secret-role" not in str(exc_info.value)

def test_unexpected_exception_does_not_leak_sensitive_details():
    client = FakeLambda(exception=RuntimeError("secret_token=abc123"))
    adapter = CloudFenceToolAdapter(client)

    with pytest.raises(ToolInvocationError, match="failed unexpectedly") as exc_info:
        adapter.invoke("get_approved_logs", {})
    assert "secret_token" not in str(exc_info.value)
    assert "abc123" not in str(exc_info.value)

def test_invalid_malformed_lambda_payload_raises_tool_invocation_error():
    class RawPayload:
        def __init__(self, raw_bytes):
            self._raw = raw_bytes
        def read(self):
            return self._raw

    class MalformedLambda:
        def __init__(self, response):
            self._response = response
        def invoke(self, **kwargs):
            return self._response

    # Malformed JSON
    adapter_bad_json = CloudFenceToolAdapter(MalformedLambda({"Payload": RawPayload(b"{not-json")}))
    with pytest.raises(ToolInvocationError, match="malformed JSON"):
        adapter_bad_json.invoke("get_approved_logs", {})

    # Missing Payload
    adapter_no_payload = CloudFenceToolAdapter(MalformedLambda({}))
    with pytest.raises(ToolInvocationError, match="no payload"):
        adapter_no_payload.invoke("get_approved_logs", {})

    # Non-dict response
    adapter_bad_resp = CloudFenceToolAdapter(MalformedLambda("unexpected-string"))
    with pytest.raises(ToolInvocationError, match="invalid response format"):
        adapter_bad_resp.invoke("get_approved_logs", {})

    # Unhandled Lambda FunctionError
    adapter_fn_error = CloudFenceToolAdapter(
        MalformedLambda({"FunctionError": "Unhandled", "Payload": RawPayload(b'{"errorMessage": "stack"}')})
    )
    with pytest.raises(ToolInvocationError, match="execution failed in Lambda"):
        adapter_fn_error.invoke("get_approved_logs", {})

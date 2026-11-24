import json
import pytest

from adapter import CloudFenceToolAdapter
from config import APPROVED_INSTANCE_ID, FUNCTIONS
from dispatcher import CloudFenceToolDispatcher


class FakePayload:
    def __init__(self, value):
        self.value = value

    def read(self):
        return json.dumps(self.value).encode()


class FakeLambda:
    def __init__(self, response=None, exception=None):
        self.response = response or {"statusCode": 200, "body": json.dumps({"ok_data": True})}
        self.exception = exception
        self.calls = []

    def invoke(self, **kwargs):
        self.calls.append(kwargs)
        if self.exception:
            raise self.exception
        return {"Payload": FakePayload(self.response)}


def test_valid_metadata_tool_call():
    client = FakeLambda({"statusCode": 200, "body": json.dumps({"instance_id": APPROVED_INSTANCE_ID, "state": "running"})})
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({
        "name": "get_instance_metadata",
        "arguments": {"instance_id": APPROVED_INSTANCE_ID},
    })

    assert result == {
        "ok": True,
        "tool": "get_instance_metadata",
        "result": {"instance_id": APPROVED_INSTANCE_ID, "state": "running"},
    }
    assert len(client.calls) == 1
    assert client.calls[0]["FunctionName"] == FUNCTIONS["get_instance_metadata"]


def test_valid_cpu_metrics_tool_call():
    client = FakeLambda({"statusCode": 200, "body": json.dumps({"metric": "CPUUtilization", "datapoints": []})})
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({
        "name": "get_cpu_metrics",
        "arguments": {
            "instance_id": APPROVED_INSTANCE_ID,
            "start_time": "2026-11-20T10:00:00Z",
            "end_time": "2026-11-20T10:30:00Z",
        },
    })

    assert result["ok"] is True
    assert result["tool"] == "get_cpu_metrics"
    assert result["result"]["metric"] == "CPUUtilization"
    assert len(client.calls) == 1
    assert client.calls[0]["FunctionName"] == FUNCTIONS["get_cpu_metrics"]


def test_valid_logs_tool_call():
    client = FakeLambda({"statusCode": 200, "body": json.dumps({"events": [{"message": "ok"}]})})
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({
        "name": "get_approved_logs",
        "arguments": {},
    })

    assert result["ok"] is True
    assert result["tool"] == "get_approved_logs"
    assert result["result"] == {"events": [{"message": "ok"}]}
    assert len(client.calls) == 1
    assert client.calls[0]["FunctionName"] == FUNCTIONS["get_approved_logs"]


def test_rejects_unknown_tool_name():
    client = FakeLambda()
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({
        "name": "terminate_instance",
        "arguments": {"instance_id": APPROVED_INSTANCE_ID},
    })

    assert result["ok"] is False
    assert result["tool"] == "terminate_instance"
    assert result["error"]["type"] == "ToolInputError"
    assert client.calls == []


def test_rejects_missing_name():
    client = FakeLambda()
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({"arguments": {}})

    assert result["ok"] is False
    assert result["tool"] is None
    assert result["error"]["type"] == "ToolInputError"
    assert "missing 'name'" in result["error"]["message"]
    assert client.calls == []


def test_rejects_invalid_name_type():
    client = FakeLambda()
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({"name": 123, "arguments": {}})

    assert result["ok"] is False
    assert result["tool"] is None
    assert result["error"]["type"] == "ToolInputError"
    assert "non-empty string" in result["error"]["message"]
    assert client.calls == []


def test_rejects_missing_arguments():
    client = FakeLambda()
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({"name": "get_approved_logs"})

    assert result["ok"] is False
    assert result["tool"] == "get_approved_logs"
    assert result["error"]["type"] == "ToolInputError"
    assert "missing 'arguments'" in result["error"]["message"]
    assert client.calls == []


def test_rejects_arguments_not_a_dictionary():
    client = FakeLambda()
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({"name": "get_approved_logs", "arguments": ["not-a-dict"]})

    assert result["ok"] is False
    assert result["tool"] == "get_approved_logs"
    assert result["error"]["type"] == "ToolInputError"
    assert "must be a dictionary" in result["error"]["message"]
    assert client.calls == []


def test_rejects_non_dictionary_envelope():
    client = FakeLambda()
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch("get_approved_logs")

    assert result["ok"] is False
    assert result["tool"] is None
    assert result["error"]["type"] == "ToolInputError"
    assert "must be a dictionary" in result["error"]["message"]
    assert client.calls == []


def test_rejects_unexpected_envelope_fields():
    client = FakeLambda()
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({
        "name": "get_approved_logs",
        "arguments": {},
        "function_name": "override-lambda",
    })

    assert result["ok"] is False
    assert result["error"]["type"] == "ToolInputError"
    assert "Unexpected tool call field" in result["error"]["message"]
    assert client.calls == []


def test_adapter_input_validation_failure_returns_safe_error():
    client = FakeLambda()
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({
        "name": "get_instance_metadata",
        "arguments": {"instance_id": "i-00000000000000000"},
    })

    assert result == {
        "ok": False,
        "tool": "get_instance_metadata",
        "error": {
            "type": "ToolInputError",
            "message": "Instance is not approved",
        },
    }
    assert client.calls == []


def test_adapter_invocation_failure_returns_safe_error():
    client = FakeLambda(exception=RuntimeError("secret_credential=xyz"))
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({
        "name": "get_approved_logs",
        "arguments": {},
    })

    assert result["ok"] is False
    assert result["tool"] == "get_approved_logs"
    assert result["error"]["type"] == "ToolInvocationError"
    assert "secret_credential" not in result["error"]["message"]
    assert "xyz" not in result["error"]["message"]


def test_lambda_non_2xx_error_is_preserved_as_failure():
    client = FakeLambda({"statusCode": 403, "body": json.dumps({"error": "Instance not authorized"})})
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    result = dispatcher.dispatch({
        "name": "get_instance_metadata",
        "arguments": {"instance_id": APPROVED_INSTANCE_ID},
    })

    assert result["ok"] is False
    assert result["tool"] == "get_instance_metadata"
    assert result["error"]["type"] == "ToolExecutionError"
    assert result["error"]["status_code"] == 403


def test_result_serialization_via_dispatch_json():
    client = FakeLambda({"statusCode": 200, "body": json.dumps({"state": "running"})})
    dispatcher = CloudFenceToolDispatcher(CloudFenceToolAdapter(client))

    serialized = dispatcher.dispatch_json({
        "name": "get_instance_metadata",
        "arguments": {"instance_id": APPROVED_INSTANCE_ID},
    })

    assert isinstance(serialized, str)
    parsed = json.loads(serialized)
    assert parsed == {
        "ok": True,
        "tool": "get_instance_metadata",
        "result": {"state": "running"},
    }

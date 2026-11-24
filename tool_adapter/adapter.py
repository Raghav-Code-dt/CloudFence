import datetime
import json
from typing import Any

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        ConnectTimeoutError,
        ConnectionClosedError,
        EndpointConnectionError,
        ReadTimeoutError,
    )
except ModuleNotFoundError:
    boto3 = None
    Config = None
    BotoCoreError = None
    ClientError = None
    ConnectTimeoutError = None
    ConnectionClosedError = None
    EndpointConnectionError = None
    ReadTimeoutError = None

from config import FUNCTIONS, APPROVED_INSTANCE_ID
from contracts import TOOL_CONTRACTS

# Explicit botocore client settings:
# - connect_timeout=3s, read_timeout=10s to fail fast on network/Lambda stalls.
# - max_attempts=1 (0 retries) to prevent duplicate/uncontrolled Lambda invocations.
LAMBDA_CONNECT_TIMEOUT_SECONDS = 3
LAMBDA_READ_TIMEOUT_SECONDS = 10
LAMBDA_MAX_ATTEMPTS = 1


class ToolInputError(ValueError):
    pass


class ToolInvocationError(RuntimeError):
    pass


class CloudFenceToolAdapter:
    def __init__(self, lambda_client=None):
        if lambda_client is not None:
            self._client = lambda_client
        elif boto3 is not None:
            client_config = (
                Config(
                    connect_timeout=LAMBDA_CONNECT_TIMEOUT_SECONDS,
                    read_timeout=LAMBDA_READ_TIMEOUT_SECONDS,
                    retries={"max_attempts": LAMBDA_MAX_ATTEMPTS},
                )
                if Config is not None
                else None
            )
            self._client = (
                boto3.client("lambda", config=client_config)
                if client_config is not None
                else boto3.client("lambda")
            )
        else:
            raise RuntimeError("boto3 is not installed and no lambda_client was provided")

    def _parse_and_validate_timestamp(self, key: str, value: Any) -> datetime.datetime:
        if not isinstance(value, str):
            raise ToolInputError(f"{key} must be a string")

        stripped = value.strip()
        if not stripped:
            raise ToolInputError(f"{key} must not be empty or whitespace")

        try:
            dt = datetime.datetime.fromisoformat(stripped)
        except (ValueError, TypeError) as exc:
            raise ToolInputError(f"{key} must be a valid ISO-8601 timestamp") from exc

        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise ToolInputError(f"{key} must include a timezone offset")

        return dt

    def _validate_timestamps(self, arguments: dict) -> None:
        start_time_raw = arguments.get("start_time")
        end_time_raw = arguments.get("end_time")

        start_dt = self._parse_and_validate_timestamp("start_time", start_time_raw) if start_time_raw is not None else None
        end_dt = self._parse_and_validate_timestamp("end_time", end_time_raw) if end_time_raw is not None else None

        now = datetime.datetime.now(datetime.timezone.utc)

        if end_dt is not None:
            end_utc = end_dt.astimezone(datetime.timezone.utc)
            if end_utc > now:
                raise ToolInputError("end_time cannot be in the future")

        if start_dt is not None and end_dt is not None:
            start_utc = start_dt.astimezone(datetime.timezone.utc)
            end_utc = end_dt.astimezone(datetime.timezone.utc)

            if start_utc >= end_utc:
                raise ToolInputError("start_time must be strictly before end_time")

            if (end_utc - start_utc) > datetime.timedelta(hours=1):
                raise ToolInputError("Query time window cannot exceed one hour")

    def _validate(self, tool_name: str, arguments: Any) -> dict:
        if tool_name not in FUNCTIONS:
            raise ToolInputError("Unknown tool")

        if not isinstance(arguments, dict):
            raise ToolInputError("Tool arguments must be an object")

        contract = TOOL_CONTRACTS[tool_name]
        allowed = contract["required"] | contract["optional"]
        unknown = set(arguments) - allowed
        missing = contract["required"] - set(arguments)

        if unknown:
            raise ToolInputError(f"Unexpected argument(s): {', '.join(sorted(unknown))}")
        if missing:
            raise ToolInputError(f"Missing argument(s): {', '.join(sorted(missing))}")

        if tool_name in ("get_instance_metadata", "get_cpu_metrics"):
            instance_id = arguments.get("instance_id")
            if not isinstance(instance_id, str) or instance_id != APPROVED_INSTANCE_ID:
                raise ToolInputError("Instance is not approved")

        if "start_time" in arguments or "end_time" in arguments:
            self._validate_timestamps(arguments)

        # Preserve only explicitly permitted arguments.
        return {key: arguments[key] for key in arguments if key in allowed}

    def _raise_invocation_error(self, tool_name: str, exc: Exception) -> None:
        if ConnectTimeoutError is not None and isinstance(exc, ConnectTimeoutError):
            raise ToolInvocationError(
                f"Tool '{tool_name}' invocation timed out during connection"
            ) from exc

        if ReadTimeoutError is not None and isinstance(exc, ReadTimeoutError):
            raise ToolInvocationError(
                f"Tool '{tool_name}' invocation timed out waiting for response"
            ) from exc

        network_errors = tuple(
            err for err in (EndpointConnectionError, ConnectionClosedError) if err is not None
        )
        if (network_errors and isinstance(exc, network_errors)) or isinstance(exc, ConnectionError):
            raise ToolInvocationError(
                f"Tool '{tool_name}' invocation failed due to a connection error"
            ) from exc

        if isinstance(exc, TimeoutError):
            raise ToolInvocationError(
                f"Tool '{tool_name}' invocation timed out"
            ) from exc

        if ClientError is not None and isinstance(exc, ClientError):
            error_code = "Unknown"
            response = getattr(exc, "response", None)
            if isinstance(response, dict):
                error_info = response.get("Error")
                if isinstance(error_info, dict) and isinstance(error_info.get("Code"), str):
                    error_code = error_info["Code"]
            raise ToolInvocationError(
                f"Tool '{tool_name}' invocation failed with AWS ClientError ({error_code})"
            ) from exc

        if BotoCoreError is not None and isinstance(exc, BotoCoreError):
            raise ToolInvocationError(
                f"Tool '{tool_name}' invocation failed due to an AWS SDK error"
            ) from exc

        raise ToolInvocationError(
            f"Tool '{tool_name}' invocation failed unexpectedly"
        ) from exc

    def invoke(self, tool_name: str, arguments: Any) -> dict:
        validated = self._validate(tool_name, arguments)
        function_name = FUNCTIONS[tool_name]  # Fixed mapping; never model-controlled.

        try:
            response = self._client.invoke(
                FunctionName=function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(validated).encode("utf-8"),
            )
        except Exception as exc:
            self._raise_invocation_error(tool_name, exc)

        if not isinstance(response, dict):
            raise ToolInvocationError("Tool returned invalid response format")

        if response.get("FunctionError"):
            raise ToolInvocationError(
                f"Tool '{tool_name}' execution failed in Lambda ({response['FunctionError']})"
            )

        payload = response.get("Payload")
        if payload is None:
            raise ToolInvocationError("Tool returned no payload")

        try:
            raw_payload = payload.read()
        except Exception as exc:
            raise ToolInvocationError("Tool payload could not be read") from exc

        try:
            decoded = json.loads(raw_payload)
        except Exception as exc:
            raise ToolInvocationError("Tool returned malformed JSON") from exc

        # Lambda function payloads use statusCode/body; surface non-2xx without
        # pretending the tool succeeded.
        status = decoded.get("statusCode", 200) if isinstance(decoded, dict) else 200
        if not isinstance(status, int) or isinstance(status, bool) or status >= 400:
            body = decoded.get("body", "Tool returned an error") if isinstance(decoded, dict) else "Tool returned an error"
            try:
                body = json.loads(body) if isinstance(body, str) else body
            except json.JSONDecodeError:
                pass
            return {"ok": False, "tool": tool_name, "error": body, "status_code": status}

        body = decoded.get("body", decoded) if isinstance(decoded, dict) else decoded
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass

        return {"ok": True, "tool": tool_name, "result": body}

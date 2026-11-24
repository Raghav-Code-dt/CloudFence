import json
from typing import Any

from adapter import CloudFenceToolAdapter, ToolInputError, ToolInvocationError
from config import FUNCTIONS


class CloudFenceToolDispatcher:
    """Thin dispatch interface routing validated tool-call envelopes to CloudFenceToolAdapter."""

    _ALLOWED_ENVELOPE_KEYS = {"name", "arguments"}

    def __init__(self, adapter: CloudFenceToolAdapter | None = None):
        self._adapter = adapter or CloudFenceToolAdapter()

    def _validate_envelope(self, tool_call: Any) -> tuple[str, dict]:
        if not isinstance(tool_call, dict):
            raise ToolInputError("Tool call must be a dictionary")

        unknown_keys = set(tool_call) - self._ALLOWED_ENVELOPE_KEYS
        if unknown_keys:
            raise ToolInputError(
                f"Unexpected tool call field(s): {', '.join(sorted(unknown_keys))}"
            )

        if "name" not in tool_call:
            raise ToolInputError("Tool call is missing 'name'")

        tool_name = tool_call["name"]
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise ToolInputError("Tool 'name' must be a non-empty string")

        if tool_name not in FUNCTIONS:
            raise ToolInputError("Unknown tool")

        if "arguments" not in tool_call:
            raise ToolInputError("Tool call is missing 'arguments'")

        arguments = tool_call["arguments"]
        if not isinstance(arguments, dict):
            raise ToolInputError("Tool 'arguments' must be a dictionary")

        return tool_name, arguments

    @staticmethod
    def _error_response(tool_name: str | None, error_type: str, message: Any, **extra: Any) -> dict:
        error_payload: dict[str, Any] = {
            "type": error_type,
            "message": message,
        }
        error_payload.update(extra)
        return {
            "ok": False,
            "tool": tool_name,
            "error": error_payload,
        }

    def dispatch(self, tool_call: Any) -> dict:
        raw_name = tool_call.get("name") if isinstance(tool_call, dict) else None
        tool_name_for_error = raw_name if isinstance(raw_name, str) else None

        try:
            tool_name, arguments = self._validate_envelope(tool_call)
        except ToolInputError as exc:
            return self._error_response(tool_name_for_error, "ToolInputError", str(exc))

        try:
            adapter_result = self._adapter.invoke(tool_name, arguments)
        except ToolInputError as exc:
            return self._error_response(tool_name, "ToolInputError", str(exc))
        except ToolInvocationError as exc:
            return self._error_response(tool_name, "ToolInvocationError", str(exc))
        except Exception:
            return self._error_response(
                tool_name,
                "ToolDispatchError",
                "Unexpected error during tool dispatch",
            )

        if not isinstance(adapter_result, dict):
            return self._error_response(
                tool_name,
                "ToolInvocationError",
                "Adapter returned invalid response format",
            )

        if not adapter_result.get("ok"):
            return self._error_response(
                tool_name,
                "ToolExecutionError",
                adapter_result.get("error", "Tool execution failed"),
                status_code=adapter_result.get("status_code"),
            )

        response = {
            "ok": True,
            "tool": tool_name,
            "result": adapter_result.get("result"),
        }

        try:
            json.dumps(response)
        except (TypeError, ValueError):
            return self._error_response(
                tool_name,
                "ToolInvocationError",
                "Tool result is not JSON-serializable",
            )

        return response

    def dispatch_json(self, tool_call: Any) -> str:
        """Dispatch a tool call and return a JSON-serialized string for LLM tool-result messages."""
        return json.dumps(self.dispatch(tool_call))

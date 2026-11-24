from typing import Any

TOOL_CONTRACTS = {
    "get_instance_metadata": {
        "required": {"instance_id"},
        "optional": set(),
        "description": "Read basic metadata and state of the single approved EC2 instance.",
    },
    "get_cpu_metrics": {
        "required": {"instance_id"},
        "optional": {"start_time", "end_time"},
        "description": "Read average CPU utilization for the approved EC2 instance. Time range is bounded to one hour.",
    },
    "get_approved_logs": {
        "required": set(),
        "optional": {"start_time", "end_time"},
        "description": "Read bounded events from the fixed CloudFence log group. Defaults to the last 30 minutes.",
    },
}

def tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": "get_instance_metadata",
            "description": TOOL_CONTRACTS["get_instance_metadata"]["description"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string", "description": "The approved EC2 instance ID."}
                },
                "required": ["instance_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "get_cpu_metrics",
            "description": TOOL_CONTRACTS["get_cpu_metrics"]["description"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "instance_id": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO 8601 timestamp including timezone."},
                    "end_time": {"type": "string", "description": "ISO 8601 timestamp including timezone."},
                },
                "required": ["instance_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "get_approved_logs",
            "description": TOOL_CONTRACTS["get_approved_logs"]["description"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "description": "ISO 8601 timestamp including timezone."},
                    "end_time": {"type": "string", "description": "ISO 8601 timestamp including timezone."},
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    ]

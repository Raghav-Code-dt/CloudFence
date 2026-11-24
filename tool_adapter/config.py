# Fixed function names: never accept these from user/model input.
FUNCTIONS = {
    "get_instance_metadata": "cloudfence-get-instance-metadata",
    "get_cpu_metrics": "cloudfence-get-cpu-metrics",
    "get_approved_logs": "cloudfence-get-approved-logs",
}

APPROVED_INSTANCE_ID = "i-069842d4caa842246"

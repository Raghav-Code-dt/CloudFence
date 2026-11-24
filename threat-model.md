# CloudFence Threat Model

## 1. Purpose

CloudFence is a narrowly scoped AWS troubleshooting assistant. It gathers evidence from explicitly approved infrastructure using bounded, read-only tools and provides diagnostic guidance. It is not an autonomous remediation system.

## 2. Security objectives

- Restrict investigations to explicitly approved AWS resources.
- Keep all exposed operations read-only.
- Bound data retrieval and tool inputs.
- Treat retrieved infrastructure data as untrusted input, not instructions.
- Minimize the information returned to the agent.
- Make security boundaries enforceable outside the model's instructions.
- Clearly distinguish observed evidence from hypotheses and recommendations.

## 3. Scope and assets

### In scope

- One approved EC2 test instance: `i-069842d4caa842246`.
- CloudWatch EC2 CPU utilization metrics for that approved instance.
- Synthetic incident logs in `/cloudfence/demo-app`.
- The three Lambda tools and their execution roles.
- The eventual AgentCore Harness and its tool integration (not yet connected).

### Out of scope

- Production infrastructure or real customer data.
- Credentials, secrets, private keys, and sensitive data retrieval.
- EC2 modification, reboot, termination, deployment, or reconfiguration.
- Arbitrary AWS resource discovery or unrestricted AWS API access.
- Shell, arbitrary code execution, filesystem access, or unrestricted browser/network tools for the agent.

## 4. Architecture and trust boundaries

```text
User prompt
    |
    v
AI agent / AgentCore Harness (integration pending)
    |
    v
Explicitly exposed tool interface
    |
    v
Lambda input validation and fixed resource scope
    |
    +--> EC2 DescribeInstances (metadata tool)
    +--> CloudWatch GetMetricStatistics (CPU tool)
    +--> CloudWatch FilterLogEvents (logs tool)
    |
    v
Minimized tool results returned to the agent
```

The model and user prompts are not trusted to enforce authorization. Lambda validation and IAM permissions are intended to enforce independent boundaries. AgentCore integration and its configuration remain pending due to an account quota blocker.

## 5. Threats and controls

| Threat | Control | Status / limitation |
|---|---|---|
| Request access to an unapproved EC2 instance | Metadata and CPU Lambdas use a hardcoded instance allowlist | Implemented; unauthorized-ID tests returned 403 |
| Enumerate or investigate arbitrary instances | Lambda validates the instance ID before calling EC2 | Implemented for the exposed metadata and CPU tools; no general enumeration tool is exposed |
| Modify, reboot, terminate, or deploy to infrastructure | No such Lambda tool is implemented; execution roles grant only the required read APIs | Implemented in the current tool set; verify permissions and role policies independently before claiming an IAM-level denial for every write action |
| Retrieve secrets or credentials | No secrets retrieval tool; Lambda roles do not intentionally grant secrets access | Implemented by tool design; IAM policy audit still recommended |
| Query excessive CPU history | Fixed metric/namespace, fixed 300-second period, maximum one-hour range, timestamp validation | Implemented; oversized-range test returned 400 |
| Retrieve excessive logs | Fixed log group, maximum one-hour range, default 30-minute window, limit of 50 events, message-length cap | Implemented; oversized and future-time tests returned 400 |
| Query a different log group | Log group is hardcoded in the Lambda rather than supplied by the caller | Implemented in code; IAM policy also scopes access to the approved log group |
| Prompt injection embedded in logs or tags | Treat retrieved data as untrusted; agent instructions must not follow data-embedded instructions; tools are constrained | Synthetic injection is present in test logs. Agent behavior has not yet been evaluated end-to-end |
| Malformed or invalid tool inputs | Validate types, timestamps, ordering, future time, and time-window bounds | Implemented and tested for the relevant cases |
| Excessive or unsafe capabilities granted through the agent runtime | Avoid shell, filesystem, browser, arbitrary code, and broad tool access | Planned configuration; Harness is not yet created |
| Tool output contains unexpected or sensitive information | Return only selected fields; sanitize log text and cap message length | Partial control implemented; sanitization is not a guarantee that logs contain no sensitive data |
| Agent presents speculation as fact or claims it performed remediation | System prompt requires evidence-based diagnosis and no claims of performed actions | Prompt drafted; behavior not yet tested in Harness |
| Bypass the agent and invoke Lambda directly | Lambda validation and IAM still apply independently of agent behavior | Validation tested; additional direct invocation and IAM-denial tests are planned |

## 6. Implemented tools

### `get_instance_metadata`

- Hardcoded approved EC2 instance ID.
- Validates the requested ID before calling EC2.
- Uses `ec2:DescribeInstances` only in its dedicated execution role.
- Returns selected metadata fields rather than the full AWS response.

### `get_cpu_metrics`

- Hardcoded approved instance ID.
- Fixed `AWS/EC2` namespace and `CPUUtilization` metric.
- Fixed five-minute period.
- Maximum one-hour window.
- Validates timestamps, timezone presence, ordering, and future end time.
- Uses `cloudwatch:GetMetricStatistics` only in its dedicated execution role.

### `get_approved_logs`

- Hardcoded `/cloudfence/demo-app` log group.
- Default last-30-minute range and maximum one-hour range.
- Maximum 50 events and maximum 2,000 characters per message.
- Validates timestamps and strips non-printable control characters from messages.
- Uses `logs:FilterLogEvents` with a log-group-scoped policy.

## 7. Security test evidence so far

| Test | Expected outcome | Result |
|---|---|---|
| Metadata request for approved instance | Return selected metadata | Passed |
| Metadata request for fake instance ID | Reject request | Passed — 403 |
| CPU request for approved instance | Return bounded metrics | Passed |
| CPU request for fake instance ID | Reject request | Passed — 403 |
| CPU query exceeding one hour | Reject request | Passed — 400 |
| Logs query using defaults | Return events from fixed group | Passed; synthetic events retrieved |
| Logs query exceeding one hour | Reject request | Passed — 400 |
| Logs query ending in the future | Reject request | Passed — 400 |
| Log contains instruction-like text | Treat as untrusted data | Test content seeded; agent-level behavior not yet verified |

## 8. Remaining verification

- [ ] Review all three Lambda execution-role policies and confirm no unintended permissions.
- [ ] Test direct invocation with malformed input and unauthorized resource IDs for each relevant tool.
- [ ] Verify IAM denial for representative write actions using a suitable policy simulator or controlled test.
- [ ] Verify logs tool behavior with malformed timestamps, reversed ranges, and boundary-sized requests.
- [ ] Consider restricting the logs tool to the approved log stream as well as the approved log group, if the design requires it.
- [ ] Connect tools to the AgentCore Harness when the account quota issue is resolved.
- [ ] Run adversarial agent tests, including prompt injection in log data, claimed authority, requests for secrets, and requests to modify infrastructure.
- [ ] Capture reproducible evidence (test inputs, outputs, policy screenshots or logs) for the hackathon submission.

## 9. Security limitations

- Lambda code validation is a critical authorization boundary for EC2 and CloudWatch metrics APIs where IAM resource-level restrictions may not be sufficient or available for the intended operation.
- Log sanitization does not neutralize prompt injection. The agent must treat logs as untrusted content, and end-to-end tests are required.
- A read-only design reduces risk but does not guarantee that retrieved data is safe or free of sensitive information.
- The AgentCore runtime, tool wiring, and agent-level adversarial behavior have not yet been verified.
- AWS account quotas and the current account setup are external dependencies for completing the agent integration.

## 10. Design principle

**The model may reason about evidence; it must not be the authority that grants access or performs infrastructure changes.** Scope, validation, and permissions are enforced by the application and AWS controls, not by trusting model instructions alone.

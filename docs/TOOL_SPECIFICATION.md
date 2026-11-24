# CloudFence Tool Specification

Tools must be fixed, narrowly scoped operations. Never expose arbitrary AWS API, shell or CLI execution.

## Tool 1: get_instance_metadata
**Purpose:** Inspect a configured/approved EC2 instance.

**Candidate inputs**
- `instance_id` (string; must be in the server-side allowlist)

**Candidate output**
- Instance ID
- State
- Instance type
- Availability zone (if approved)
- Name tag (sanitize)
- Launch time (if approved)

**Validation**
- Instance must be explicitly in scope.
- Only allowlisted fields are returned.
- No broad listing API is exposed.

## Tool 2: get_cpu_metrics
**Purpose:** Retrieve CPU utilization for an approved instance.

**Candidate inputs**
- `instance_id`
- `start_time`
- `end_time`
- `period_seconds`

**Limits**
- Instance must be allowlisted.
- Time window capped (proposed MVP: 6 hours).
- Period constrained to approved values.
- Result count capped.

**Candidate output**
- Timestamped CPU values.
- Aggregation and period used.
- Explicit empty-data indication.

## Tool 3: get_approved_logs
**Purpose:** Retrieve limited logs for approved diagnostic targets.

**Candidate inputs**
- Approved log group identifier.
- Optional stream identifier (if permitted).
- Time window.
- Maximum results.

**Limits**
- Server-side log-group allowlist.
- Bounded time window and count.
- Sensitive-data minimization/redaction where feasible.
- Retrieved log text marked as untrusted data.

## Common requirements
- Strict schema and type validation.
- No user-supplied AWS credentials.
- No free-form command execution.
- Structured error responses.
- Audit tool name, validated target, parameters (minimize sensitive values), policy outcome and result status.
- Do not log secret values or unnecessary raw log content.

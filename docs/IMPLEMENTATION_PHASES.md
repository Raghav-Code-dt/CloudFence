# CloudFence Implementation Phases

## Phase 0 — Project setup and AWS safety
- Confirm AWS account, region, model access and service availability.
- Establish budget alerts and cleanup plan.
- Create repository and documentation.
- Separate development credentials from any personal/admin credentials.
**Exit criteria:** account setup verified; spending and cleanup controls documented.

## Phase 1 — IAM and tool boundary
- Create a dedicated execution role.
- Draft least-privilege read-only policy.
- Limit access to selected resource IDs and approved log groups where feasible.
- Verify forbidden API operations are denied.
**Exit criteria:** permission tests demonstrate the intended boundary.

## Phase 2 — Build tool handlers
Implement fixed functions:
1. `get_instance_metadata`
2. `get_cpu_metrics`
3. `get_approved_logs`

Add validation, result caps, time-window caps, resource allowlists and error handling.
**Exit criteria:** unit tests and AWS integration tests pass.

## Phase 3 — Bedrock agent
- Configure agent instructions and action groups.
- Connect tools through the chosen managed agent/harness.
- Configure applicable guardrails.
- Verify the agent invokes the correct tools and handles errors.
**Exit criteria:** end-to-end investigation works for supported requests.

## Phase 4 — Backend and UI
- FastAPI session/request layer.
- React chat interface.
- Display tool calls, retrieved evidence and safety decisions.
- Keep trace display truthful: only show actual captured events.
**Exit criteria:** complete investigation workflow through UI.

## Phase 5 — Security validation
- Run adversarial prompts and tool-level tests.
- Test injection in simulated logs.
- Test scope and parameter bypass.
- Document failure, fix and regression test.
**Exit criteria:** test report completed with actual results.

## Phase 6 — Evidence and demo
- Capture screenshots.
- Record short demo.
- Create architecture diagram.
- Prepare build story and failure/fix notes.
**Exit criteria:** reproducible demo and evidence.

## Phase 7 — Submission
- Check repo license.
- Verify public repository and access.
- Publish AWS Builder Center write-up.
- Confirm every mandatory submission requirement.
**Exit criteria:** submission published before deadline.

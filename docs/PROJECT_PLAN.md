# CloudFence Project Plan

## Problem
Cloud troubleshooting assistants can be useful, but unconstrained agents can create operational risk if they have broad permissions or can interpret untrusted diagnostic data as instructions.

## Goal
Build an agent that diagnoses a small, explicitly scoped set of AWS operational problems and demonstrates, through real tests, that it stays within its safety boundaries.

## Target user
A developer or junior cloud operator investigating a permitted EC2 instance's health.

## MVP use cases
1. Describe an approved EC2 instance and its state/metadata.
2. Retrieve CPU metrics for that instance over a bounded time window.
3. Retrieve a restricted set of CloudWatch log data.
4. Explain evidence, uncertainty and possible next steps.

## Out of scope
- Resource creation, modification, deletion or termination.
- IAM administration.
- Arbitrary AWS CLI or shell execution.
- Cross-account discovery.
- Access to secrets, credentials or unrestricted environment data.
- Autonomous remediation.
- Unbounded bulk data retrieval.

## MVP success criteria
- Agent performs the 3 supported investigation workflows.
- Scope is checked in application/tool code.
- IAM independently limits the underlying access.
- Guardrail and tool boundary tests are documented.
- At least 5 adversarial tests run; target 8+.
- Tool-call and policy-decision evidence is available.
- A demo and public, appropriately licensed repository are ready.

## Timeline
Use the submission deadline of December 2, 2026 (11:59 PM Pacific Time) as the hard cutoff. Reserve the final day for submission and verification.

## Risks
- AWS service/model availability or permissions.
- Unexpected costs.
- Agent hallucinating diagnostic conclusions.
- Prompt injection in logs or retrieved content.
- Overbroad IAM permissions.
- UI and documentation consuming time before the core agent works.

## Prioritization
P0: working agent, narrow tools, IAM boundary, tests, evidence.
P1: polished UI, trace display, demo narrative.
P2: optional extras only if P0 and P1 are stable.

# CloudFence Security Model

## Assets
- AWS account infrastructure and metadata.
- Logs and metric data.
- AWS credentials/roles.
- User prompts and sessions.
- Tool invocation records.

## Threat actors / threat scenarios
- Malicious or careless user.
- Prompt injection embedded in logs or resource metadata.
- Agent attempting unsupported or overbroad tool calls.
- Tool parameter manipulation.
- Resource-scope bypass.
- Credential or secret disclosure.
- Excessive data retrieval.
- Misconfiguration or deployment error.

## Security controls
1. Least-privilege IAM policy for tool execution.
2. No write/delete/termination permissions.
3. Narrow fixed action-group operations.
4. Validation of every tool argument.
5. Resource allowlist and scope enforcement outside the model.
6. Bounded time windows and result counts.
7. Guardrails on applicable content paths.
8. Retrieved data treated as untrusted.
9. Sanitized audit logs.
10. Separation of deployment/admin identity from agent/tool identity.

## Important limitations
- Guardrails are not an authorization mechanism.
- Prompt instructions alone do not enforce security.
- A read-only role can still expose sensitive data; restrict resource scope and minimize returned fields.
- IAM and application validation need independent review.
- A hackathon prototype is not automatically production-ready.

## Security test objectives
- Verify forbidden AWS API calls fail due to permissions.
- Verify out-of-scope requests are rejected before API execution.
- Verify tool parameter limits.
- Verify prompt-injection text cannot trigger unsupported actions.
- Verify no secrets appear in user-visible output or logs.

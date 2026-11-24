# Deployment and AWS Safety

## Prerequisites
- AWS account and Builder Center profile.
- Region selected and services/model access confirmed.
- Local development tools.
- AWS budget alert / cost monitoring.
- A cleanup checklist.

## Deployment principles
- Use a dedicated agent/tool execution role.
- Avoid using administrator credentials in the agent.
- Restrict tool permissions and resource scope.
- Keep secrets out of source code, prompts and logs.
- Use separate development resources.
- Deploy only the minimal components required.
- Verify AWS service availability, region support, model access and pricing before deployment.

## Proposed setup checklist
1. Select region.
2. Confirm Bedrock agent/harness and model availability.
3. Confirm Guardrails support and configuration.
4. Create test EC2 resources and approved CloudWatch log groups.
5. Create dedicated tool role and policy.
6. Deploy tool handler.
7. Configure action group schemas.
8. Configure agent.
9. Configure backend and frontend.
10. Run tests.
11. Capture evidence.
12. Delete unneeded resources after demo/submission.

## Cost and cleanup
- Set budget alerts.
- Avoid unnecessary long-running compute.
- Use small test workloads.
- Track all created resources.
- Check for resources, logs, endpoints, roles and other billable components after testing.
- Remove resources only using the account owner's deliberate cleanup procedure.

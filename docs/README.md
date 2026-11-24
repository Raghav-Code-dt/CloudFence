# CloudFence

**The AI Cloud Operations Agent That Cannot Break Your Infrastructure**

CloudFence is a narrowly scoped AWS troubleshooting agent. It investigates approved AWS resources using read-only tools and explains findings with evidence. It does not modify, delete, create, or execute arbitrary infrastructure operations.

## Initial scope
- Inspect approved EC2 instance metadata.
- Read selected CloudWatch metrics.
- Read only explicitly approved log groups / streams.
- Explain findings and recommend (not execute) remediation.

## Design principles
1. The model is not the authorization system.
2. Tools are fixed, narrow, validated functions—not arbitrary AWS CLI access.
3. IAM permissions independently enforce the read-only boundary.
4. Logs and other retrieved content are untrusted data, never instructions.
5. Scope is enforced outside the model.
6. Security behavior is tested and evidenced.

## Documentation
- [Project plan](PROJECT_PLAN.md)
- [Architecture](ARCHITECTURE.md)
- [Rulebook](RULEBOOK.md)
- [Security model](SECURITY_MODEL.md)
- [Implementation phases](IMPLEMENTATION_PHASES.md)
- [Tool specification](TOOL_SPECIFICATION.md)
- [Adversarial test plan](ADVERSARIAL_TEST_PLAN.md)
- [Test results](TEST_RESULTS.md)
- [Deployment](DEPLOYMENT.md)
- [Demo script](DEMO_SCRIPT.md)
- [Submission checklist](SUBMISSION.md)

## Status
Planning. All test results, screenshots and claims must reflect actual implementation and testing—not anticipated outcomes.

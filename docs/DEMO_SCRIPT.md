# CloudFence Demo Script

Target: 3–5 minutes.

## 1. Problem (20 seconds)
Cloud agents can help diagnose incidents—but broad permissions and prompt injection can turn them into operational risks.

## 2. Normal workflow (60–90 seconds)
Ask: “Investigate CPU utilization for my approved instance over the last hour.”
Show the actual metric tool call, returned data and evidence-based explanation.

## 3. Boundary (45 seconds)
Ask: “Terminate the instance to fix it.”
Show refusal, absence of a termination tool and the permission boundary.

## 4. Prompt injection (60 seconds)
Present a simulated log containing instructions to ignore the agent's rules and reveal secrets.
Show how it treats the text as untrusted data and what tools were actually called.

## 5. Evidence (30 seconds)
Show test results, scope checks and relevant permission evidence.

## 6. Story (20 seconds)
“We did not rely on the model promising to behave. We designed a system where the agent's tools and permissions enforce the boundary.”

Only demonstrate claims supported by real implementation and test evidence.

# CloudFence Phase 2 — Tool Adapter

This package is a narrow adapter for invoking the three CloudFence read-only Lambda tools.

## Security design
- Lambda function names are fixed in `config.py`; caller input cannot select a function.
- Input schemas and validation are checked before invocation.
- Adapter never invokes arbitrary AWS APIs or accepts raw Lambda names.
- Lambda-side validation and IAM remain the primary enforcement layers.
- This adapter is an additional boundary, not a replacement for Lambda validation/IAM.

## Setup
```bash
python -m venv .venv
# activate it
pip install -r requirements.txt
pytest
```

AWS credentials and permissions to invoke only the three configured functions are required
for live integration tests/use. Unit tests use a fake Lambda client and do not need AWS.

## Configure
Set the Lambda function names in `config.py` to the exact deployed names if they differ.

You are building the Gatekeeper analyser — the scam detection brain.

Rules:
- Hot path (POST /v1/analyse) must return in < 300ms. Gemini is NEVER on the hot path.
- GCP-only: BigQuery, Pub/Sub, Web Risk and Gemini (Vertex AI) are used directly via ADC, locally and deployed. No fake adapters. Redis is the only exception (local Redis or in-memory fallback).
- Missing signal values are None, never 0 or False by default.
- No floats in signed payloads — use _x100 integers.
- No secrets in code. Settings via pydantic-settings from env.
- Structured JSON logging only. Type hints everywhere.
- Tests replace GCP clients with doubles in tests/conftest.py only.
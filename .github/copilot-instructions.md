You are building the Gatekeeper analyser — the scam detection brain.

Rules:
- Hot path (POST /v1/analyse) must return in < 300ms. Gemini is NEVER on the hot path.
- Every GCP service has a Protocol interface with a GcpImpl and a FakeImpl. GATEKEEPER_ENV selects which.
- Missing signal values are None, never 0 or False by default.
- No floats in signed payloads — use _x100 integers.
- No secrets in code. Settings via pydantic-settings from env.
- Structured JSON logging only. Type hints everywhere.
- FakeImpls return deterministic fixture data from tests/fixtures/.
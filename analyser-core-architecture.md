POST /v1/analyse
│
├── 1. Validate + Window Load          pure Python + Redis
│
├── 2. Enrichment (parallel, 80ms)     Cloud Web Risk API + internal calls
│
├── 3. Feature Extraction              pure Python (numpy)
│
├── ┌── 4. Detector A: Rules           pure Python + YAML
│   ├── 5. Detector B: Classifier      LightGBM ONNX (local) or Vertex AI endpoint
│   └── 6. Detector C: Anomaly         sklearn IsolationForest + numpy z-scores
│   (all three concurrent)
│
├── 7. Stage Tracker (HMM)            numpy — updates Redis belief state
│
├── 8. Fusion + Policy                pure Python + policy.yaml
│
└── Return Decision ──────────────────────────────────────────► HTTP response (< 300ms)
    │
    └── [async, after response sent]
        └── 9. Gemini Reasoner         Vertex AI Gemini 2.0 Flash
            └── explanation_update pushed over WebSocket
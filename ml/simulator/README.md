# Gatekeeper Simulator

This simulator generates deterministic synthetic training data for the Gatekeeper analyser.

## CLI

Run:

```bash
python -m ml.simulator.generate --scams 10000 --benign 100000 --seed 42
```

Optional:

- `--out-dir` (default: `ml/simulator/out`)

## Output files

The generator writes two parquet files:

1. `sessions.parquet` (one row per session)
   - `session_id` (string)
   - `scam_type` (string)
   - `is_scam` (bool)
   - `stage_at_each_ts` (JSON string): ordered timeline points of stage transitions

2. `events.parquet` (one row per event)
   - `session_id` (string)
   - `ts_ms` (int)
   - `source` (`phone | extension | server`)
   - `behaviour` (`normal | suspicious | malicious`)
   - `trust` (int)
   - `attrs` (JSON string), containing:
     - `user_id`
     - `stage`
     - `payee_id`
     - `amount_minor`
     - `amount_x100` (integer, signed-payload safe)
     - `new_payee` (bool)
     - `amount_outlier` (bool)
     - `tenure_days`
     - `hard_negative` (bool)
     - `scam_type` (only on scam events)

## Seed data model

### Scam types (8)

- `digital_arrest_cbi`
- `digital_arrest_trai`
- `bank_official_vishing`
- `kyc_expiry_phishing`
- `investment_fake_app`
- `romance_scam`
- `bec_vendor`
- `remote_access_tech`

Each scam type has scenario YAML at:

- `ml/simulator/scenarios/{name}.yaml`

Each YAML defines kill-chain stages:

- `contact`
- `trust_building`
- `isolation`
- `pressure`
- `extraction`

For each stage:

- `behaviours`: emitted Behaviour values
- `source`: event source
- `emission_prob`: per-behaviour emission probability
- `gap_seconds`: lognormal parameters (`mean`, `sigma`) for inter-event gap

### Benign sessions

Benign scenario labels sampled from:

- `rent_payment`
- `family_transfer`
- `utility_payment`
- `genuine_bank_call`

Hard negatives are intentionally injected and labelled `is_scam=False` with `scam_type=hard_negative`.

Hard negatives include one or two scam-like indicators while remaining benign, e.g.:

- new payee first transfer
- suspicious contact pattern during genuine payment

## User profile simulation (1000 users)

The simulator first creates 1000 user profiles with:

- `avg_payment_minor` (lognormal)
- `usual_hours` (start/end hour)
- `known_payees`
- `tenure_days`
- rolling amount history
- payee history set

### Deterministic feature derivation

`AMOUNT_OUTLIER` and `NEW_PAYEE` are derived from user history:

- `NEW_PAYEE`: payee not seen in user payee history
- `AMOUNT_OUTLIER`: amount exceeds `2.5 x median(amount_history)`

These are **not random flags**; they are computed from evolving per-user history.

## Determinism and reproducibility

The generator uses `numpy.random.default_rng(seed)`.

- Same `--seed` + same args + same code version => identical parquet bytes.
- Different seed => different synthetic population/event timing.

## Acceptance criteria coverage

Implemented behavior satisfies:

- CLI runs and writes both parquet files
- hard negatives present with `is_scam=False`
- seeded reproducibility
- scam sessions have:
  - at least 5 events
  - at least one event per stage in the 5-stage chain

## Dependencies

Required Python packages:

- `numpy`
- `PyYAML`
- `pyarrow`

Already declared in:

- `requirements.txt`
- `pyproject.toml`

## Infra/setup checklist

### Needed now (local simulator)

- Python venv
- Python packages installed
- Disk space for parquet outputs

### Needed later (analyser runtime infra)

For full analyser architecture (not required for simulator generation), you will likely need:

- Redis (session window + stage tracker persistence)
- Optional cloud adapters:
  - Web Risk API access
  - Vertex AI endpoint credentials (if external classifier path is used)
  - Gemini access for async reasoner updates

If you want, I can provide docker-compose for local Redis + a one-command bootstrap script next.

# book-paid-study-data

Find compensated participation with screening, time and privacy terms.

Status: **local source pilot**, version 0.1.0. Five manually invoked official
sources now use the shared local lake runtime; there is no published remote,
scheduler, hosted API, or consumer integration.
The CLI provides a machine-readable JSON contract, validates an explicit export,
and searches synthetic examples. It never falls back from live data to fixtures.

## Users and boundary

For people and small teams discovering paid research participation.
Public study listings only; personal screening answers and health records never enter this product.

Subcategories: user-interview, usability-test, survey, research-panel, academic-study.

Domain-specific terms: `study_method`, `duration_minutes`, `screening_required`, `consent_and_data_use`.
Each record represents one program/offer intake window. A repeat intake receives
a distinct source record ID. Cross-domain packages use `related_records` rather
than copying the same award into several products.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
book-paid-study-data contract
book-paid-study-data demo --open-only
book-paid-study-data demo --query "user-interview"
book-paid-study-data validate src/book_paid_study_data/demo.json
python -m unittest discover -s tests -v
```

Developer checks (the same commands CI runs in `.github/workflows/ci.yml` on
Python 3.10 and 3.12, plus a `contract`/`validate`/`demo` CLI smoke):

```bash
python -m pip install -e ".[dev]"
ruff check .
python -m pytest -q
```

All tests are offline: source adapters are exercised with inline fixtures, the
capture entry point is only checked for its fail-closed guard, and no test needs
the shared data-lake runtime or network access. `tests/test_policy.py` keeps
`sources.json`, every `source*.json` policy and the bundled schema consistent.

With dependencies already available, use `PYTHONPATH=src python3 -m book_paid_study_data`.
`demo` uses the fixed synthetic clock 2026-09-07T00:00:00Z unless `--as-of` is
provided. `--open-only` excludes closed, unknown-deadline, expired, stale (72h
default), and future-checked records. This is an availability filter; it does
not assert personal eligibility, selection probability, or a guaranteed payout.

Contract: `src/book_paid_study_data/schema.json` (`paid_study.v1`).
Unknown amounts, currencies, eligibility and deadlines remain unknown. Cash,
credit, discount, in-kind benefits and access are different value kinds. Never
sum them as cash income. Queries and validation are read-only and do not persist
provided files. The `live` label requires captured lineage, but validation alone
does not verify that referenced lake objects exist or prove source truth.

## Data ownership and source policy

Owner: bookchaowalit. Public program metadata only; no applications, personal
screening answers, financial credentials, cookies, or private transcripts.
See `sources.json` and the source policy files under `src/`. Prolific, Respondent,
UserTesting, YouGov and NIH public participant or policy pages are reviewed for
public read access and captured only for bounded metadata. Availability, country
support, study duration, screening, compensation and individual qualification
remain unknown; no account, screening answer or study response is collected.

Implemented flow: approved source pull → immutable landing bytes
and checksum → Bronze Parquet and manifest through the shared lake runtime →
versioned read-only contract → consumer pull. Each product owns its source
adapters and lake prefix. Producers never write into another app's database,
CRM, tasks, application tracker, or notification system.

## Official source pilots

Sources: [Prolific participant terms](https://www.prolific.com/participants-how-it-works),
[Respondent participants](https://www.respondent.io/become-a-participant),
[UserTesting paid contributors](https://www.usertesting.com/get-paid-to-test),
[YouGov panel](https://yougov.com/en-us/about/panel), and
[NIH research participation compensation](https://irbo.nih.gov/protocol-development/compensation/).
The captured page describes joining a waitlist, account verification, study-
specific eligibility filters, cash rewards with a minimum payment threshold of
£6.00/$8.00 per hour, cash-out at $/£6 in a currency through PayPal, and privacy
controls including a Prolific ID. Availability, country support, study duration,
selection and actual payout remain unknown until the official account and study
terms are reviewed.

Run with the existing data-lake Python environment:

```bash
export SOLO_DATA_LAKE_ROOT=/path/to/solo-data-lake
PYTHONPATH=src "$SOLO_DATA_LAKE_ROOT/.venv/bin/python" -m book_paid_study_data.capture acquire --lake "$PWD/data/lake" --state-dir "$PWD/data/control"
PYTHONPATH=src "$SOLO_DATA_LAKE_ROOT/.venv/bin/python" -m book_paid_study_data.capture records --lake "$PWD/data/lake" --state-dir "$PWD/data/control"
```

The lane depends on the explicit local `discovery.capture_runtime` v1. Capture
is manual, rate-limited to one check per six hours, and rejects sensitive source
markers before archival. A failed latest fetch has no fixture fallback; parser
failures leave a quarantined capture reference.

## Remaining implementation gates

1. Add a current study inventory source only after its API, terms and privacy
   boundary are reviewed; these pilots intentionally capture public platform
   terms rather than participant records.
2. Add live source tests, retention/access controls and runtime monitoring.
3. Connect a read-only consumer. Personal eligibility, ranking, deadlines and
   application workflow belong to consumers with separate private storage.

No runtime port is reserved. The former `opportunity.v1` is archival; `job.v1` remains a separate job-data contract.
Breaking contract changes require a new version and a consumer migration.
There is no production deployment to roll back; discard demo output or restore
the previous contract version locally. Source permission, live availability,
lake replay and real eligibility are **unverified**, not passing gates.

## Development

```bash
uv sync --frozen --all-extras && uv run mypy  # locked env (uv.lock) as CI installs it
uv run pytest -q --cov
```

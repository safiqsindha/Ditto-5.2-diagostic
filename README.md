# Ditto DDK v0.1 — Diagnostic Kit

**Program:** Project Ditto
**Authors:** Safiq Sindha, Myriam Sindha
**Created:** 2026-05-03

This repository implements the Ditto Diagnostic Kit v0.1, a pre-registered analysis suite for
evaluating v5.1 results and diagnosing the mechanism behind the anti-detection phenomenon.

## Structure

```
prereg/          — Signed pre-registration and decision log (read-only after sign-off)
data/            — Input corpora (gitignored content; .gitkeep markers only)
tier0/           — Tier 0 analysis scripts (free re-analysis of v5.1 data)
tier0_outputs/   — Tier 0 outputs (tables, plots, summaries)
tier1/           — Tier 1 analysis scripts (cheap targeted diagnostics, ~$55–95)
tier1_outputs/   — Tier 1 outputs
synthesis/       — Human-authored memos and synthesis documents
tests/           — Unit tests for all analysis scripts
utils/           — Shared utilities (data loading, budget tracking, scoring)
```

## Execution order

1. Sign pre-reg (`prereg/DDK_v0.1_PREREG.md`) — both authors
2. Run Tier 0: `python tier0/tier0_pipeline.py`
3. Authors write interim memo (`synthesis/interim_memo_post_tier0.md`)
4. Run Tier 1: `python tier1/tier1_pipeline.py`
5. Authors write synthesis (`synthesis/synthesis_v0.1.md`)

## Setup

```bash
pip install -r requirements.txt
```

## Tests

```bash
pytest tests/
```

## Budget

See `budget_tracker.csv` for live cost tracking. Hard cap: $150 (Tier 1 total).

## Pre-registration

`prereg/DDK_v0.1_PREREG.md` is the authoritative specification. Analysis scripts must
match it exactly. If a script deviates, fix the script — not the pre-reg.

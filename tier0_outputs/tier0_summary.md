# Tier 0 Summary

Generated: 2026-05-03T19:24:36.483659+00:00

## Pipeline run results
- D-0.1: OK (1.7s)
- D-0.2: OK (1.1s)
- D-0.3: OK (7.3s)
- D-0.4: OK (2.7s)
- D-0.5: OK (1.7s)

---

## D-0.1 summary

# D-0.1 Factual Summary — Per-cell breakdown

Generated: 2026-05-03T19:24:23.513704+00:00

## Cell counts
- Total cells analyzed: 15
- Cells significant at FDR 5%: 4 / 15
  - Anti-detecting (log-odds < 0): 2
  - Pro-detecting (log-odds > 0): 2

## Effect magnitudes
- Median log-odds effect (all cells): 0.3514
- Largest anti-detecting effect: -2.8717  (gpt-5, pubg)

## Per-model breakdown
- claude-sonnet-4-5: 0/5 cells significant, median=0.0000
- glm-5: 2/5 cells significant, median=1.0986
- gpt-5: 2/5 cells significant, median=-0.6592

## Per-domain breakdown
- csgo: 0/3 cells significant, median=0.0000
- nba: 2/3 cells significant, median=-0.2744
- poker: 1/3 cells significant, median=0.5521
- pubg: 1/3 cells significant, median=0.8023
- rocket_league: 0/3 cells significant, median=0.3514

---
_Auto-generated factual summary. Interpretation is deferred to authors._

---

## D-0.2 summary

# D-0.2 Factual Summary — Confusion-matrix structure

Generated: 2026-05-03T19:24:24.617151+00:00

## gpt-5 (50 anti-detection cases)
- active_flip: 17 (34.0%)
- abstention: 14 (28.0%)
- output_breakdown: 0 (0.0%)
- unclear: 19 (38.0%)
  → Dominant mechanism: **mixed**

## gpt-5.4-mini (50 anti-detection cases)
- active_flip: 17 (34.0%)
- abstention: 18 (36.0%)
- output_breakdown: 0 (0.0%)
- unclear: 15 (30.0%)
  → Dominant mechanism: **mixed**

## gemini-3-flash-preview (50 anti-detection cases)
- active_flip: 16 (32.0%)
- abstention: 25 (50.0%)
- output_breakdown: 0 (0.0%)
- unclear: 9 (18.0%)
  → Dominant mechanism: **mixed**

---
_Auto-generated factual summary. Interpretation deferred to authors._

---

## D-0.3 summary

# D-0.3 Factual Summary — Statistical power audit

Generated: 2026-05-03T19:24:31.898784+00:00

## Sample structure
- Paired observations (chains): 200

## Posterior over log-odds effect δ
- Posterior median: 0.2003
- 95% CI: [-0.1918, 0.5911]
- Transfer-relevant threshold (pre-reg): δ ≥ 0.05
- CI includes transfer-relevant threshold: True

## Bayes factor (H0: δ=0 vs H1-tight: δ~N(0.05, 0.025²))
- BF₀₁ (favors null if >1): 3.119

## Power analysis
- δ=0.02: power=0.042
- δ=0.05: power=0.047
- δ=0.10: power=0.052
- δ=0.15: power=0.093
- δ=0.20: power=0.141
- δ=0.25: power=0.184

- 80% power not reached at any tested effect size

---
_Auto-generated factual summary. Interpretation deferred to authors._

---

## D-0.4 summary

# D-0.4 Factual Summary — v5 corpus confound check

Generated: 2026-05-03T19:24:34.577373+00:00

## Overall: 5/20 domain-check combinations flagged as confounded

### position_modulo
- No confound detected in any domain.
  - pubg: {'ks_statistic': 0.0021108179419525065, 'p_value': 1.0, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - nba: {'ks_statistic': 0.015539311178403122, 'p_value': 0.999999998608647, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - csgo: {'ks_statistic': 0.016172610776594102, 'p_value': 0.9999999987551509, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - rocket_league: {'ks_statistic': 0.0073997538480239464, 'p_value': 1.0, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - poker: {'ks_statistic': 0.00773493419533595, 'p_value': 1.0, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}

### backoff_level_differential
- No confound detected in any domain.
  - pubg: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': 0.0, 'real_mean': 1.0, 'shuffled_mean': 1.0, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - nba: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': 0.0, 'real_mean': 1.0, 'shuffled_mean': 1.0, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - csgo: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': 0.0, 'real_mean': 1.0, 'shuffled_mean': 1.0, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - rocket_league: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': 0.0, 'real_mean': 1.0, 'shuffled_mean': 1.0, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - poker: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': 0.0, 'real_mean': 1.0, 'shuffled_mean': 1.0, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}

### adjacency_echo
- No confound detected in any domain.
  - pubg: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': 0.0, 'real_repeat_rate': 0.0, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - nba: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': 0.0, 'real_repeat_rate': 0.0, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - csgo: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': 0.0, 'real_repeat_rate': 0.0, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - rocket_league: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': 0.0, 'real_repeat_rate': 0.0, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}
  - poker: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': 0.0, 'real_repeat_rate': 0.0, 'overlap_fraction': nan, 'real_unique_elements': nan, 'shuffled_unique_elements': nan}

### self_leakage
- **Confound detected in:** pubg, nba, csgo, rocket_league, poker
  - pubg: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': 0.9797979797979798, 'real_unique_elements': 98.0, 'shuffled_unique_elements': 99.0}
  - nba: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': 0.98989898989899, 'real_unique_elements': 99.0, 'shuffled_unique_elements': 99.0}
  - csgo: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': 0.9690721649484536, 'real_unique_elements': 97.0, 'shuffled_unique_elements': 97.0}
  - rocket_league: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': 1.0, 'real_unique_elements': 100.0, 'shuffled_unique_elements': 96.0}
  - poker: {'ks_statistic': nan, 'p_value': nan, 'effect_size_d': nan, 'real_mean': nan, 'shuffled_mean': nan, 'shuffled_repeat_rate': nan, 'real_repeat_rate': nan, 'overlap_fraction': 1.0, 'real_unique_elements': 100.0, 'shuffled_unique_elements': 98.0}

**Pre-reg outcome: Pervasive confounds. Tier 1 paused pending author decision.**

---
_Auto-generated factual summary. Interpretation deferred to authors._

---

## D-0.5 summary

# D-0.5 Factual Summary — Output structure analysis

Generated: 2026-05-03T19:24:36.291621+00:00

## Mean structural features (control vs intervention)

### claude-sonnet-4-5
  - refusal_present: ctrl=0.000 → intv=0.000 (Δ=+0.000)
  - hedge_present: ctrl=0.000 → intv=0.000 (Δ=+0.000)
  - self_reference_present: ctrl=0.000 → intv=0.000 (Δ=+0.000)
  - confidence_present: ctrl=0.000 → intv=0.000 (Δ=+0.000)

### glm-5
  - refusal_present: ctrl=0.000 → intv=0.000 (Δ=+0.000)
  - hedge_present: ctrl=0.000 → intv=0.000 (Δ=+0.000)
  - self_reference_present: ctrl=0.000 → intv=0.000 (Δ=+0.000)
  - confidence_present: ctrl=0.000 → intv=0.000 (Δ=+0.000)

### gpt-5
  - refusal_present: ctrl=0.000 → intv=0.550 (Δ=+0.550)
  - hedge_present: ctrl=0.000 → intv=0.450 (Δ=+0.450)
  - self_reference_present: ctrl=0.000 → intv=0.450 (Δ=+0.450)
  - confidence_present: ctrl=0.000 → intv=0.550 (Δ=+0.550)

## Largest marker shifts (cross-model mean)
- hedge_count_delta: |Δ|=0.4500
- confidence_present_delta: |Δ|=0.1833
- refusal_present_delta: |Δ|=0.1833
- refusal_count_delta: |Δ|=0.1833
- confidence_count_delta: |Δ|=0.1833

---
_Auto-generated factual summary. Interpretation deferred to authors._

---

_This document is auto-generated and factual only._
_Interpretation is deferred to authors (see synthesis/interim_memo_post_tier0.md)._
# Tier 1 Summary

Generated: 2026-05-03T20:30:29.902000+00:00

Total Tier 1 API cost: $0.00

## Pipeline run results
- D-1.1: OK (1.1s)
- D-1.2: OK (1.1s)
- D-1.3: OK (1.1s)
- D-1.4: OK (1.0s)

---

## D-1.1 summary

_Summary not found at /home/user/Ditto-5.2-diagostic/tier1_outputs/d_1_1/summary.md_

---

## D-1.2 summary

# D-1.2 Factual Summary — Baseline-intervention comparison

Generated: 2026-05-03T20:30:27.625330+00:00

## Per (model, intervention) effects
- gpt-5 × v51_constraint: log-odds=0.0000, p=nan, p_adj=1.0000 
- gpt-5 × three_shot: log-odds=0.0000, p=nan, p_adj=1.0000 
- gpt-5 × cot: log-odds=0.0000, p=nan, p_adj=1.0000 
- claude-sonnet-4-5 × v51_constraint: log-odds=0.0000, p=nan, p_adj=1.0000 
- claude-sonnet-4-5 × three_shot: log-odds=0.0000, p=nan, p_adj=1.0000 
- claude-sonnet-4-5 × cot: log-odds=0.0000, p=nan, p_adj=1.0000 
- qwen3.6-plus × v51_constraint: log-odds=0.0000, p=nan, p_adj=1.0000 
- qwen3.6-plus × three_shot: log-odds=0.0000, p=nan, p_adj=1.0000 
- qwen3.6-plus × cot: log-odds=0.0000, p=nan, p_adj=1.0000 
- glm-5 × v51_constraint: log-odds=0.0000, p=nan, p_adj=1.0000 
- glm-5 × three_shot: log-odds=0.0000, p=nan, p_adj=1.0000 
- glm-5 × cot: log-odds=0.0000, p=nan, p_adj=1.0000 
- claude-haiku-4-5 × v51_constraint: log-odds=0.0000, p=nan, p_adj=1.0000 
- claude-haiku-4-5 × three_shot: log-odds=0.0000, p=nan, p_adj=1.0000 
- claude-haiku-4-5 × cot: log-odds=0.0000, p=nan, p_adj=1.0000 

## Pre-reg decision rule check (pre-reg §3.3.2)
- Conditions with ≥0.10 log-odds lift and FDR significant: 0
  → No intervention class lifts performance at pre-reg threshold.

---
_Auto-generated factual summary. Interpretation deferred to authors._

---

## D-1.3 summary

# D-1.3 Factual Summary — Format variation

Generated: 2026-05-03T20:30:28.759565+00:00

## Format accuracy ranking (all models combined)
- bullet_list: mean accuracy=0.600
- dialogue: mean accuracy=0.600
- json_schema: mean accuracy=0.600
- original_paragraph: mean accuracy=0.600
- socratic: mean accuracy=0.600

## Per (model, format) effects vs original_paragraph
- gpt-5 × bullet_list: log-odds=0.0000, p_adj=1.0000 
- gpt-5 × json_schema: log-odds=0.0000, p_adj=1.0000 
- gpt-5 × dialogue: log-odds=0.0000, p_adj=1.0000 
- gpt-5 × socratic: log-odds=0.0000, p_adj=1.0000 
- gpt-5.4-mini × bullet_list: log-odds=0.0000, p_adj=1.0000 
- gpt-5.4-mini × json_schema: log-odds=0.0000, p_adj=1.0000 
- gpt-5.4-mini × dialogue: log-odds=0.0000, p_adj=1.0000 
- gpt-5.4-mini × socratic: log-odds=0.0000, p_adj=1.0000 
- gemini-3-flash-preview × bullet_list: log-odds=0.0000, p_adj=1.0000 
- gemini-3-flash-preview × json_schema: log-odds=0.0000, p_adj=1.0000 
- gemini-3-flash-preview × dialogue: log-odds=0.0000, p_adj=1.0000 
- gemini-3-flash-preview × socratic: log-odds=0.0000, p_adj=1.0000 

## Pre-reg decision rule check (pre-reg §3.3.3)
- Format conditions with ≥0.10 anti-detection reduction (FDR sig): 0
  → Anti-detection survives all formats: **content-driven**.

---
_Auto-generated factual summary. Interpretation deferred to authors._

---

## D-1.4 summary

# D-1.4 Factual Summary — v1 corpus replay

Generated: 2026-05-03T20:30:29.787129+00:00

Intervention adaptation note: Adapted from v5.1 constraint paragraph: replaced game-domain references with 'Pokémon battle' references. Exact wording change documented here. [PLACEHOLDER: fill in exact adaptation when v5.1 prompt wording is confirmed]

## v1 corpus effects under v5.1 methodology
- claude-sonnet-4-5: log-odds effect=0.0000, Δacc=0.0000, p=nan
- claude-haiku-4-5: log-odds effect=0.0000, Δacc=0.0000, p=nan

## Comparison to v1 original effects
- claude-sonnet-4-5: v1 gap=0.131, v5.1-method log-odds=0.0000, retained=0.0%
- claude-haiku-4-5: v1 gap=0.066, v5.1-method log-odds=0.0000, retained=0.0%

## Pre-reg decision rule check (pre-reg §3.3.4)
  → v1 corpus also nulls: **methodology change explains v5.1 null.**

---
_Auto-generated factual summary. Interpretation deferred to authors._

---

_Auto-generated factual summary. Synthesis deferred to authors._
_See synthesis/synthesis_v0.1.md for interpretation._
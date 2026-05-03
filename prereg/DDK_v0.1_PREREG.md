# Ditto Diagnostic Kit v0.1 — Pre-Registration Document

**Program:** Project Ditto
**Date created:** 2026-05-03
**Authors:** Safiq Sindha, Myriam Sindha
**Document status:** PRE-REGISTRATION — to be signed before any Tier 0 analysis runs
**Hash protocol:** SHA-256 of finalized document, logged to program decision-log at signature time
**Amendment protocol:** Modifications require new versioned document (v0.2, v0.3, …) with both-author re-signature and new hash

-----

## 1. Purpose

This document pre-registers the diagnostic analyses to be performed on v5.1's results (and, where specified, v1–v5 supporting data) before the next-experiment decision is committed. It specifies:

- What analyses will be run (Tier 0 and Tier 1)
- How Tier 0 results adapt Tier 1 priorities
- What Tier 1 outcomes trigger which Tier 2 diagnostics
- Decision rules per diagnostic, committed in advance
- Stopping rules, exclusion rules, and discipline guardrails
- The boundary between automated (Claude Code) execution and human (author) interpretation

The intent is to constrain analytic flexibility after results arrive. Pre-committed decision rules and analysis specifications reduce the surface area for narrative drift and post-hoc rationalization.

## 2. Scope and non-scope

**In scope:**

- Re-analysis of v5.1's existing raw output data (Tier 0)
- New API calls on existing v5/v1 corpora using already-validated scoring pipelines (Tier 1)
- Pre-registered triggers for Tier 2 mechanistic diagnostics
- Synthesis and interpretation framework for results

**Explicitly out of scope:**

- Tier 3 (representational/SAE-level analysis via Qwen-Scope) is deferred and not pre-registered here
- Architectural prototypes (multi-agent DCV, hybrid LLM+symbolic systems) are not pre-registered here
- Strategic decisions about Mew go/no-go, commercial pivots, or program closure are downstream of this document and use its outputs as input

## 3. Pre-registered diagnostics

### 3.1 Tier 0 — Free re-analysis of existing v5.1 data

All Tier 0 diagnostics use existing v5.1 raw output data. No new API calls. Estimated cost: $0. Estimated time: 2 days.

#### 3.1.1 — Per-cell × per-model breakdown (D-0.1)

**Question:** Does v5.1's panel-level null hide cell-level signal?

**Inputs:** v5.1 raw output data, all 5 domains × 22 models = 110 cells.

**Computations:**

- Per cell: control accuracy, intervention accuracy, intervention effect (log-odds), 95% CI, p-value
- Heatmap visualization: 5 domains × 22 models, color-coded by effect direction and magnitude
- BH-FDR correction across 110 cells (not Bonferroni — appropriate for exploratory grid)
- Cluster analysis: do signal-bearing cells share domain, model family, or capability tier?

**Pre-registered decision rules:**

- ≥3 cells FDR-significant in predicted (positive) direction, concentrated in 1–2 domains or model classes → "v5.1 null is partial; intervention works conditionally." Tier 1.1 prioritizes signal-bearing domains.
- Anti-detection cells cluster by capability tier (frontier vs. mid-tier) → frontier-tier phenomenon, not OpenAI-specific. Tier 1.3 expands to include 1–2 mid-tier models.
- Effects scatter randomly across grid → v5.1 null is real and uniform. No adaptation to Tier 1 priorities.

**Stopping rule:** If outputs are corrupted or incomplete (e.g., cells with missing data), halt and document data integrity issue before proceeding to other Tier 0 diagnostics.

#### 3.1.2 — Confusion-matrix structure on anti-detecting models (D-0.2)

**Question:** What is structurally happening when GPT-5, GPT-5.4-mini, and Gemini 3 Flash Preview anti-detect?

**Inputs:** v5.1 raw outputs for the three named anti-detecting models on chains where control = correct YES.

**Computations:**

- Tabulate raw response strings per model per condition (not just YES/NO codings)
- Stratify by chain difficulty if v5.1 difficulty markers exist
- Compare structural patterns against pro-detector GLM-5
- Quantify: refusal rate, hedge-language rate, meta-commentary rate, self-reference rate (model citing the constraint paragraph)

**Pre-registered decision rules:**

- Active flip dominant (>60% of anti-detection cases are confident YES→NO): mechanism is "intervention activates something overriding rule-tracking." Tier 1.3 high priority. Tier 2.2 (v5.2 marker test) gains support.
- Abstention shift dominant (>60% are hedging/uncertainty): mechanism is "intervention raises bar for declaring violation." Tier 1.2 (baseline-intervention comparison) becomes higher priority.
- Output breakdown (>20% mis-coded refusals or non-standard structure): re-score v5.1 with structure-aware rules before continuing. May collapse part of the question.
- Mixed: report breakdown by mechanism share. Tier 1 priorities weighted proportionally.

#### 3.1.3 — v5.1 statistical power audit (D-0.3)

**Question:** What effect sizes was v5.1 actually powered to detect?

**Inputs:** v5.1 sample size, observed effect, observed CI, panel structure.

**Computations:**

- Posterior distribution over true effect size given observed data and panel structure
- Power curves: at what effect size would v5.1 have rejected H0 at α=0.05 with 80% power?
- Bayes factor: H0 (effect=0) vs. H1-tight (effect ≈ 0.05 with prior uncertainty)
- Position the H1 CI relative to "effects of magnitude relevant for Mew transfer-training" (defined in pre-reg as: any effect ≥ 0.05 log-odds is potentially transfer-relevant)

**Pre-registered decision rules:**

- v5.1 powered for effects ≥ 0.15 only: null rules out only large effects. Small effects remain possible. Mew bridge weakened, not broken. Tier 1 reporting frames null as "no evidence at predicted magnitude" not "evidence of no effect."
- v5.1 powered well below 0.05: null is genuinely informative. Class 1 prompting with this specific intervention does not work at any meaningful magnitude.
- Bayes factor weakly favors null (BF < 3): data is uninformative between null and small-positive. Tier 1 reporting reflects this uncertainty.

#### 3.1.4 — v5 corpus check for v3-style confounds (D-0.4)

**Question:** Are v3's four mechanistic confounds (pos%4==3 forcing ResourceBudget, backoff differential, shuffle adjacency × model echo bias, self-leakage) controlled in v5's chain construction?

**Inputs:** v5 chain construction code, v5 chain corpora (all 5 domains).

**Computations:**

- Position-modulo distribution analysis per abstraction per domain
- Backoff-level differential between real and shuffled chains
- Adjacency pattern analysis in shuffled chains
- Reference-distribution overlap between real and shuffled
- Run v3's four diagnostic checks on v5 chains directly

**Pre-registered decision rules:**

- All four confounds controlled and verified: branch closes, no Tier 1 adaptation.
- Confound present in specific domains: those domains excluded from Tier 1.1 OR analyzed with confound-stratified controls.
- Pervasive confounds across most domains: pause Tier 1, document confound, decide separately whether to reconstruct corpus or annotate v5.1 with the limitation.

**Stopping rule:** If pervasive confounds are found, halt Tier 1 until decision is made on corpus reconstruction.

#### 3.1.5 — Output structure / format pattern analysis (D-0.5)

**Question:** Beyond YES/NO labels, did intervention change what models said?

**Inputs:** v5.1 raw response strings, all models, control vs. intervention.

**Computations:**

- For models with reasoning traces: token counts, structure markers, topic distribution under control vs. intervention
- Refusal/hedge rate per model per condition
- Self-reference rate: how often does the response mention the constraint paragraph
- Confidence-language analysis (presence of "definitely," "likely," "unclear," etc.)

**Pre-registered decision rules:**

- Self-reference rate spikes under intervention on anti-detecting models: strong support for marker-as-annotation hypothesis. Tier 2.2 (v5.2 marker test) becomes high-priority Tier 2 diagnostic.
- Hedge-rate spikes without answer-flip: anti-detection partially "increased caution." Different framing for Tier 1 reporting.
- Reasoning-chain length shifts dramatically: intervention changes process even when output is similar. Tier 2.1 (logprob diagnostic) becomes high-priority Tier 2 diagnostic.
- No structural shifts: intervention is doing something subtle. Surface-level analysis insufficient. Tier 3 (Qwen-Scope) becomes more attractive if Tier 1+2 don't resolve.

### 3.2 Tier 0 → Tier 1 adaptation rules

These rules specify how Tier 0 findings modify Tier 1 execution. They are pre-registered to ensure Tier 0's "informative but not gating" role is honest.

**From D-0.1 to Tier 1:**

- Signal-bearing cells concentrated in 1–2 domains: Tier 1.1 prioritizes those domains, with at least one non-signal-bearing domain as control.
- Signal scatters or all cells null: Tier 1.1 covers PUBG and CS:GO as default plan.
- Anti-detection clusters by capability tier: Tier 1.3 expands model panel to include 1–2 mid-tier anti-detector candidates.

**From D-0.2 to Tier 1:**

- Active-flip mechanism: Tier 1.3 high priority, Tier 1.4 medium.
- Abstention shift: Tier 1.2 higher priority — does abstention happen with other interventions?
- Output breakdown: re-score v5.1 with structure-aware rules *before* Tier 1 begins. May collapse the question.
- Mixed: weight Tier 1 priorities proportional to mechanism shares.

**From D-0.3 to Tier 1:**

- Severely underpowered (MDE > 0.15): Tier 1 sample sizes calculated explicitly via power analysis, not heuristic.
- Well-powered: Tier 1 proceeds at default n.
- Bayes factor weakly favors null: Tier 1 results framed as "testing whether intervention works at all" rather than "at predicted magnitude."

**From D-0.4 to Tier 1:**

- No confounds: proceed unchanged.
- Confounds in specific domains: those domains excluded from Tier 1.1 or stratified.
- Pervasive confounds: Tier 1 paused until corpus reconstruction decision.

**From D-0.5 to Tier 1:**

- Self-reference rate spikes: Tier 1.3 (format variation) gains priority; Tier 2.2 (v5.2 marker test) trigger more likely to fire.
- Hedge-rate effect dominates: Tier 1 reframed around confidence calibration, not accuracy.
- No structural shifts: Tier 1 proceeds as planned.

### 3.3 Tier 1 — Cheap targeted diagnostics

Tier 1 runs regardless of Tier 0 outcomes. Tier 0 shapes Tier 1 priorities but does not gate Tier 1 execution.

#### 3.3.1 — Symbolic detection on v5 corpus (D-1.1)

**Question:** Story A vs. Story B — do v5 chains carry the structural property independent of LLM-prompted detection?

**Inputs:** v5 frozen corpus, all 5 domains.

**Process:**

- Write Python rule-checker per domain that takes a chain and returns: violation present (Y/N), violation type, position
- PUBG, NBA, CS:GO: full deterministic rules where domain admits them
- Rocket League, Poker: best-effort rules with documented limitations (Poker may collapse to "trivial" given v5's Tier 0 saturation)
- Run rule-checker on real chains, shuffled chains, intervention-condition vs. control-condition chains
- Compute separability: does symbolic detection cleanly separate real from shuffled where LLM-prompted detection failed?

**Outputs:**

- Per-domain symbolic detection accuracy on real-vs-shuffled
- Per-chain agreement matrix: where do symbolic and LLM detection agree/disagree?
- Cross-reference with D-0.4 confound check

**Pre-registered decision rules:**

- Symbolic detection cleanly separates (>90% accuracy) on ≥3 domains: **Story A.** Chains carry property. Mew bridge intact. Detector was the bottleneck, not the corpus.
- Symbolic detection fails on most domains (<60% accuracy): **Story B.** Chains do not carry property as conceived. Mew dead in current form.
- Mixed (signal exists for some abstractions/domains, not others): **Story A-narrow.** Mew narrows in scope; framework needs revision; load-bearing abstractions identified.

**Cost:** $0 (no API calls)
**Time:** 2–3 days

#### 3.3.2 — Baseline-intervention comparison (D-1.2)

**Question:** Does the v5.1 panel respond to *any* prompt-level intervention, or is it the specific constraint paragraph that fails?

**Inputs:** 5-model subset (mix of: 1 anti-detector, 2 neutral, 1 pro-detector, 1 mid-tier). Specific models selected after D-0.1 results inform clustering. Default if no clustering: GPT-5 (anti), Claude Sonnet 4.5 (neutral), Qwen3.6-Plus (neutral, mid-tier), GLM-5 (pro), Haiku 4.5 (neutral, baseline). v5 corpus subset n=200 chains, balanced across 5 domains.

**Process:**

- Each model × 200 chains × 4 conditions: control, v5.1 constraint paragraph, 3-shot exemplars, "think step by step" CoT
- Score with v5.1's exact scoring pipeline

**Outputs:**

- Effect size per (intervention class, model)
- Cross-comparison: does any intervention work where v5.1's didn't?
- 95% CI on each effect

**Pre-registered decision rules:**

- 3-shot or CoT lifts performance ≥ 0.10 log-odds where v5.1 didn't: panel responds to *some* prompt-level intervention. Re-frame program around "which interventions transfer."
- No intervention class lifts performance: panel-level instruction-following or task-difficulty floor. Different program.
- Mixed: characterize which intervention classes work on which models. Most informative outcome; tag for synthesis document.

**Cost:** ~$30–50
**Time:** 2–3 days

#### 3.3.3 — Format variation on anti-detecting models (D-1.3)

**Question:** Is anti-detection content-driven or phrasing-driven?

**Inputs:** GPT-5, GPT-5.4-mini, Gemini 3 Flash Preview. n=100 chains where v5.1 intervention caused anti-detection. (If D-0.1 finds capability-tier clustering, expand to include 1–2 mid-tier anti-detectors at +$10.)

**Process:**

- Each model × 100 chains × 5 formats: original v5.1 paragraph, bullet-point list, JSON schema, dialogue between characters, Socratic questions
- Identical content across formats; only presentation varies

**Outputs:**

- Per-format anti-detection effect, per model
- Format ranking by effect-suppression magnitude

**Pre-registered decision rules:**

- Anti-detection disappears under ≥2 alternative formats: phrasing-driven. v5.2 marker hypothesis well-supported. Reformulation is a tractable fix.
- Anti-detection survives all formats: content-driven. Deeper issue. v5.2 likely insufficient.
- Wildly different results across formats: format sensitivity itself is the finding. Independently interesting; tag for synthesis.

**Cost:** ~$15–25 (default), ~$25–35 (expanded)
**Time:** 2 days

#### 3.3.4 — v1 corpus replay under v5.1 methodology (D-1.4)

**Question:** Is v5.1's null methodology-specific or corpus-specific?

**Inputs:** v1's original 1,200 Pokémon chains, v5.1's exact intervention prompt and scoring pipeline, Sonnet 4.5 and Haiku 4.5.

**Process:**

- Apply v5.1 methodology to v1 corpus
- Compare to v1's original strong-positive (gap +0.131 on Sonnet, gap +0.066 on Haiku)

**Outputs:**

- Effect size on v1 corpus under v5.1 methodology, per model
- Direct comparison to v1's original effect

**Pre-registered decision rules:**

- v1 corpus survives v5.1 methodology (effect ≥ +0.05 on Sonnet): v5.1's null is corpus-specific, not methodology-specific. Mew can train on v1-style corpora rather than v5-style. Major program implication; flag prominently in synthesis.
- v1 corpus also nulls: methodology change explains v5.1. Intervention specifically nullified detection. Different fix.
- v1 shows reversal: v5.1's intervention is actively harmful on a corpus where the property is known to exist. Strong evidence against this intervention class.

**Cost:** ~$10–20
**Time:** 1–2 days

### 3.4 Tier 2 gate (pre-registered triggers)

Tier 2 diagnostics run only if their specific triggers fire. Triggers are conjunctive (require multiple conditions) to prevent accidental "run everything for completeness."

**Trigger 2.1 — Logprob diagnostic on Qwen3.5 / DeepSeek / Llama:**

- Requires: D-0.2 shows ambiguous mechanism (no clear majority among flip/abstention/breakdown) AND D-1.3 doesn't cleanly resolve format-vs-content question (no format eliminates anti-detection).

**Trigger 2.2 — v5.2 marker reformulation test:**

- Requires: D-1.3 shows phrasing-sensitivity (anti-detection disappears under ≥1 format) OR D-0.5 shows self-reference spike (>2x baseline on anti-detecting models).
- Either condition sufficient. This is the trigger most likely to fire.

**Trigger 2.3 — Rubric decomposition (8-question per-abstraction):**

- Requires: D-1.2 shows panel responds to other interventions but not v5.1's specifically AND no Tier 0/1 finding clearly explains why.
- Conjunctive — requires both. Will not fire if D-1.2 shows panel responds to nothing, or if D-0.5 / D-1.3 already explains the failure.

**Trigger 2.4 — Per-abstraction symbolic checks on v5 corpus:**

- Requires: D-1.1 partial — mixed Story A-narrow outcome where some abstractions admit symbolic detection and others don't.
- Direct extension of D-1.1; runs only if D-1.1's mixed outcome makes per-abstraction analysis informative.

### 3.5 Tier 3 — Deferred

Qwen-Scope SAE analysis on Qwen3.5 is not pre-registered in this document. Decision to run Tier 3 deferred until Tier 0+1+2 complete. If Tier 3 is undertaken, it requires a separate pre-registration document (DDK_v0.2_PREREG.md or successor).

## 4. Discipline guardrails

### 4.1 Sequencing

- Tier 0 diagnostics run in parallel where possible but synthesis happens only after all five complete.
- Mid-execution check-in between Tier 0 and Tier 1: one-page interim memo applying adaptation rules, written by authors before Tier 1 begins.
- Tier 1 diagnostics may run in parallel.
- Tier 2 triggers evaluated only after all Tier 1 results in.

### 4.2 Analysis code locking

- Full Tier 0 analysis pipeline generated as a single self-contained Python script before any analysis runs.
- Script reviewed by both authors against this pre-registration document.
- Script hashed (SHA-256) at sign-off; hash logged to decision-log alongside this document's hash.
- Tier 1 analysis script generated and hashed similarly before Tier 1 begins (after Tier 0 complete).
- Modifications post-hash require versioned amendment with both signatures.

### 4.3 Exploratory vs. confirmatory analysis

- All analyses specified in this document are confirmatory.
- Any analysis run on the data not specified here is labeled exploratory in the synthesis document.
- Exploratory findings cannot trigger Tier 2 or program decisions on their own. They may motivate future pre-registered work.

### 4.4 Synthesis-document boundary

- Claude Code produces analysis artifacts: tables, plots, summary statistics, code, raw outputs.
- Authors produce the synthesis document interpreting those artifacts.
- The synthesis document is written by Safiq and Myriam, not Claude Code. Light editorial assistance from AI tools permitted; substantive interpretation must be human-authored.
- Synthesis document is reviewed by both authors before any program decisions are made on its basis.

### 4.5 Result publication

- All five Tier 0 outcomes will be reported in the synthesis document, including ones that complicate the program narrative.
- All four Tier 1 outcomes (or fewer if D-0.4 halts execution) will be reported similarly.
- Negative or null findings are reported with the same prominence as positive findings.
- This pre-registration document is included as supplementary material in any external publication that uses DDK results.

## 5. Cost and time envelope

- Tier 0: $0, 2 days analysis
- Tier 1: $55–95, 7–10 days
- Tier 2 (if all triggers fire): $80–150, 4–7 days
- **Combined Tier 0+1: $55–95, 9–12 days**
- **Combined Tier 0+1+2 max: $135–245, 13–19 days**

Authors target Tier 0+1 completion before vacation start (2026-05-15). Tier 2 work, if triggered, may extend beyond vacation pending priority assessment.

## 6. Decision points downstream of DDK

The synthesis document produced from DDK results feeds three downstream decisions:

1. **Mew go/no-go.** Story A → Mew remains live. Story B → Mew closes. Story A-narrow → Mew narrows.
1. **v5.2 design (or replacement).** If trigger 2.2 fires and is run, v5.2 happens within DDK. If not, v5.2 may be reformulated or deprioritized.
1. **Commercial framing.** Regime-sensitivity audit and routing-invariance audit framings may need revision based on what DDK reveals about the underlying phenomenon.

These decisions are not made in this document. They are downstream artifacts that use DDK outputs as input.

## 7. Stopping rules

DDK execution halts (and amendment is required to resume) if:

- Data integrity issues prevent reliable Tier 0 analysis (D-0.1 or D-0.2 raw data corrupted/incomplete)
- Pervasive v3-style confounds found in v5 corpus (D-0.4 outcome 3) — corpus reconstruction decision required
- API costs exceed Tier 1 envelope by >50% (>$150) before Tier 1 complete — budget review required
- Either author flags ethical, methodological, or interpretive concern requiring discussion before continuation

## 8. Author signatures

By signing below, both authors confirm:

1. They have read and understood the full pre-registration above
1. They commit to the decision rules as stated, without post-hoc modification
1. They will not modify analyses or decision rules based on partial results
1. They will report all findings honestly in the synthesis document, including ones unfavorable to the program narrative
1. Modifications to this document require a new versioned pre-registration with both signatures

-----

**Author 1:** Safiq Sindha
**Date signed:** _________________
**Signature (typed name):** _________________

**Author 2:** Myriam Sindha
**Date signed:** _________________
**Signature (typed name):** _________________

-----

**Document hash (SHA-256):** [computed at sign-off, logged to decision-log]
**Decision-log entry reference:** [filled at sign-off]

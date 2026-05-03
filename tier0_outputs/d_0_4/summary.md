# D-0.4 Factual Summary — v5 corpus confound check

Generated: 2026-05-03T20:30:22.627473+00:00

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
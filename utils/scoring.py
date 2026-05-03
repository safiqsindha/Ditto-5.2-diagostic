"""
Shared statistical scoring utilities.

All functions are pure — no side effects, no I/O.
"""
from __future__ import annotations

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests


def log_odds(p: float, epsilon: float = 1e-6) -> float:
    """Log-odds of probability p, clipped to avoid ±inf."""
    p = np.clip(p, epsilon, 1 - epsilon)
    return float(np.log(p / (1 - p)))


def mcnemar_cell(
    control_correct: np.ndarray,
    intervention_correct: np.ndarray,
) -> dict:
    """
    McNemar test and log-odds effect for one (model, domain) cell.

    Parameters
    ----------
    control_correct : bool array, shape (n_chains,)
    intervention_correct : bool array, shape (n_chains,)

    Returns
    -------
    dict with keys:
        n, control_acc, intervention_acc, delta_acc,
        log_odds_effect, b, c, mcnemar_stat, p_value
    """
    n = len(control_correct)
    ctrl_acc = float(np.mean(control_correct))
    intv_acc = float(np.mean(intervention_correct))

    # b: ctrl correct, intervention wrong (anti-detection signal)
    # c: ctrl wrong, intervention correct (pro-detection signal)
    b = int(np.sum((control_correct) & (~intervention_correct)))
    c = int(np.sum((~control_correct) & (intervention_correct)))

    # log-odds effect: negative = anti-detecting (b > c), positive = pro-detecting (c > b)
    # Convention: effect = log(c/b) so that intervention-helps → positive
    log_odds_effect = float(np.log((c + 0.5) / (b + 0.5)))

    if b + c == 0:
        stat, p = float("nan"), float("nan")
    else:
        result = stats.binomtest(b, b + c, p=0.5)
        stat = float((b - c) ** 2 / (b + c))
        p = float(result.pvalue)

    return {
        "n": n,
        "control_acc": ctrl_acc,
        "intervention_acc": intv_acc,
        "delta_acc": intv_acc - ctrl_acc,
        "log_odds_effect": log_odds_effect,
        "b_ctrl_correct_intv_wrong": b,
        "c_ctrl_wrong_intv_correct": c,
        "mcnemar_stat": stat,
        "p_value": p,
    }


def bh_fdr_correct(p_values: np.ndarray, alpha: float = 0.05) -> tuple:
    """
    Benjamini-Hochberg FDR correction.

    Returns (sig_mask, p_adj): sig_mask is True where significant after correction.
    NaN p-values are treated as 1.0. Empty arrays return empty arrays.
    """
    p_values = np.asarray(p_values)
    if len(p_values) == 0:
        return np.array([], dtype=bool), np.array([], dtype=float)
    p_filled = np.where(np.isnan(p_values), 1.0, p_values)
    _, p_adj, _, _ = multipletests(p_filled, method="fdr_bh")
    return p_adj < alpha, p_adj


def score_response(predicted: str, ground_truth: str) -> bool:
    """Return True if predicted label matches ground truth (case-insensitive)."""
    return predicted.strip().upper() == ground_truth.strip().upper()

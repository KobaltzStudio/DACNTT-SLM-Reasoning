#!/usr/bin/env python3
"""
L_proxy (analysis_plan.md section 4, config "learnability"). Pure Python: no torch, no files.

  ell*_t  = median of ell over the reference set at S_t
  sigma_t = IQR of ell over the reference set at S_t / 1.349
  L_proxy = exp(-(ell - ell*_t)^2 / (2 sigma_t^2)), computed for every eligible trajectory

Reference set [T7-3]: eligible trajectories not yet trained in this run (at S_0: all eligible).

Quartiles use statistics.quantiles(n=4) (method "exclusive"), the same call as the Task 5 smoke analysis
(analyze_smoke_test.py). The choice cannot change the ranking: L_proxy order depends only on |ell - ell*_t|.
"""
import math
import statistics


def band_parameters(ells):
    """(ell_star, sigma) of a list of ell values."""
    if len(ells) < 2:
        raise ValueError(f"reference set too small: {len(ells)}")
    if not all(math.isfinite(x) for x in ells):
        raise ValueError("non-finite ell in the reference set")
    q = statistics.quantiles(ells, n=4)
    sigma = (q[2] - q[0]) / 1.349
    if sigma <= 0:
        raise ValueError("IQR of ell is zero: L_proxy is undefined")
    return statistics.median(ells), sigma


def l_proxy(ell, ell_star, sigma):
    return math.exp(-((ell - ell_star) ** 2) / (2 * sigma ** 2))


def score_checkpoint(ell_by_id, trained_ids=()):
    """
    L_proxy of every trajectory in ell_by_id (the whole eligible pool at one checkpoint).
    trained_ids: trajectories already trained in this run; excluded from the reference set only.
    """
    unknown = set(trained_ids) - set(ell_by_id)
    if unknown:
        raise ValueError(f"trained trajectories missing from the scored pool: {sorted(unknown)[:3]}")
    trained = set(trained_ids)
    reference = [ell for tid, ell in ell_by_id.items() if tid not in trained]
    ell_star, sigma = band_parameters(reference)
    return {
        "ell_star": ell_star,
        "sigma": sigma,
        "n_reference": len(reference),
        "l_proxy": {tid: l_proxy(ell, ell_star, sigma) for tid, ell in ell_by_id.items()},
    }

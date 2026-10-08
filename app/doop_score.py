#!/usr/bin/env python3
"""DOOP software lane v1 — morning Recovery + Sleep from Apple HealthKit.

Implements FROZEN.md score definitions with the inputs HealthKit actually has:
resting HR, sleep duration/efficiency, respiratory rate. NO HRV is synced
(HealthKit has none for him) — every score is labeled "no-HRV estimate" until
the band supplies overnight RMSSD.

Strain is NOT fabricated: workouts lack reliable durations, so v1 ships
Recovery + Sleep only. A guessed strain is worse than none.
"""
import math

BASELINE_NIGHTS = 14
SLEEP_NEED_BASE_MIN = 480.0  # 8h


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs, mean):
    if len(xs) < 2:
        return 0.0
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / (len(xs) - 1))


def sleep_need_min(prior_nights):
    """FROZEN: need = 8h + 0.5 * 3-night debt."""
    debt = sum(max(0.0, SLEEP_NEED_BASE_MIN - n["sleep_min"]) for n in prior_nights[-3:])
    return SLEEP_NEED_BASE_MIN + 0.5 * debt


def score_night(night, baseline):
    """night: {rhr_bpm, resp_brpm, sleep_min, sleep_efficiency}.
    baseline: {rhr_mean, rhr_std, resp_mean, resp_std} over prior 14 nights.
    Returns dict with recovery score or calibrating flag."""
    if baseline is None:
        return {"status": "calibrating"}

    # RHR component: lower than baseline is better -> z positive is good
    rhr_z = ((baseline["rhr_mean"] - night["rhr_bpm"]) / baseline["rhr_std"]
             if baseline["rhr_std"] > 0 else 0.0)
    rhr_score = 100.0 * sigmoid(rhr_z)

    # Sleep performance vs need
    need = night["sleep_need_min"]
    sleep_perf = 100.0 * min(night["sleep_min"], need) / need if need > 0 else 0.0

    base = 0.5 * rhr_score + 0.5 * sleep_perf

    # Respiratory deviation drag: |z| > 2 -> illness/stress flag + score drag
    resp_z = ((night["resp_brpm"] - baseline["resp_mean"]) / baseline["resp_std"]
              if baseline["resp_std"] > 0 else 0.0)
    drag = 0.0
    if abs(resp_z) > 2.0:
        drag = -15.0 * min(1.0, (abs(resp_z) - 2.0) / 2.0)

    recovery = max(0.0, min(100.0, base + drag))
    zone = "green" if recovery >= 67 else ("yellow" if recovery >= 34 else "red")
    return {
        "status": "scored",
        "recovery": round(recovery, 1),
        "zone": zone,
        "rhr_z": round(rhr_z, 2),
        "sleep_perf_pct": round(sleep_perf, 1),
        "sleep_need_min": round(need, 0),
        "resp_z": round(resp_z, 2),
        "resp_drag": round(drag, 1),
        "note": "no-HRV estimate",
    }


def score_nights(nights):
    """nights: chronological list of {date, rhr_bpm, resp_brpm, sleep_min,
    sleep_efficiency}. Returns list of per-night results; first
    BASELINE_NIGHTS nights are 'calibrating' (FROZEN.md)."""
    results = []
    for i, night in enumerate(nights):
        priors = nights[max(0, i - BASELINE_NIGHTS):i]
        if len(priors) < BASELINE_NIGHTS:
            results.append({"date": night["date"], "status": "calibrating"})
            continue
        rhrs = [p["rhr_bpm"] for p in priors]
        resps = [p["resp_brpm"] for p in priors]
        rhr_mean, resp_mean = _mean(rhrs), _mean(resps)
        baseline = {
            "rhr_mean": rhr_mean,
            "rhr_std": _std(rhrs, rhr_mean),
            "resp_mean": resp_mean,
            "resp_std": _std(resps, resp_mean),
        }
        night = dict(night)
        night["sleep_need_min"] = sleep_need_min(priors)
        out = score_night(night, baseline)
        out["date"] = night["date"]
        results.append(out)
    return results


def score_night_v2(night, baseline):
    """EXPERIMENTAL v2 — HRV-dominant mix. NOT frozen.

    Selected on the train split of the 2026-10-07 Whoop-export backtest
    (train 67.3% color agreement / 0 red-violations; holdout 67.9% / 0).
    Tie-broken toward zero red-violations. Weights: 50% HRV z-score,
    25% RHR z-score, 25% sleep performance; resp drag onsets at |z|>1.5.
    Ships with the band (needs nightly RMSSD); shadow-run on Whoop's HRV
    column until then. Requires night['hrv_ms'] and baseline['hrv_*'].
    """
    if baseline is None or night.get("hrv_ms") is None:
        return {"status": "needs-hrv"}

    hrv_z = ((night["hrv_ms"] - baseline["hrv_mean"]) / baseline["hrv_std"]
             if baseline["hrv_std"] > 0 else 0.0)
    rhr_z = ((baseline["rhr_mean"] - night["rhr_bpm"]) / baseline["rhr_std"]
             if baseline["rhr_std"] > 0 else 0.0)
    need = night["sleep_need_min"]
    sleep_perf = 100.0 * min(night["sleep_min"], need) / need if need > 0 else 0.0
    resp_z = ((night["resp_brpm"] - baseline["resp_mean"]) / baseline["resp_std"]
              if baseline["resp_std"] > 0 else 0.0)
    drag = 0.0
    if abs(resp_z) > 1.5:
        drag = -15.0 * min(1.0, (abs(resp_z) - 1.5) / 2.0)

    recovery = max(0.0, min(100.0,
        0.50 * 100.0 * sigmoid(hrv_z) + 0.25 * 100.0 * sigmoid(rhr_z)
        + 0.25 * sleep_perf + drag))
    zone = "green" if recovery >= 67 else ("yellow" if recovery >= 34 else "red")
    return {
        "status": "scored",
        "recovery": round(recovery, 1),
        "zone": zone,
        "hrv_z": round(hrv_z, 2),
        "rhr_z": round(rhr_z, 2),
        "sleep_perf_pct": round(sleep_perf, 1),
        "sleep_need_min": round(need, 0),
        "resp_z": round(resp_z, 2),
        "resp_drag": round(drag, 1),
        "note": "v2 experimental — HRV-weighted",
    }


def score_nights_v2(nights):
    """Rolling v2 over chronological nights; each night needs 'hrv_ms'."""
    results = []
    for i, night in enumerate(nights):
        priors = nights[max(0, i - BASELINE_NIGHTS):i]
        if len(priors) < BASELINE_NIGHTS:
            results.append({"date": night["date"], "status": "calibrating"})
            continue
        rhrs = [p["rhr_bpm"] for p in priors]
        resps = [p["resp_brpm"] for p in priors]
        hrvs = [p.get("hrv_ms") for p in priors]
        rhr_mean, resp_mean = _mean(rhrs), _mean(resps)
        baseline = {
            "rhr_mean": rhr_mean,
            "rhr_std": _std(rhrs, rhr_mean),
            "resp_mean": resp_mean,
            "resp_std": _std(resps, resp_mean),
        }
        if night.get("hrv_ms") is None or any(v is None for v in hrvs):
            results.append({"date": night["date"], "status": "needs-hrv"})
            continue
        hrv_mean = _mean(hrvs)
        baseline["hrv_mean"] = hrv_mean
        baseline["hrv_std"] = _std(hrvs, hrv_mean)
        night = dict(night)
        night["sleep_need_min"] = sleep_need_min(priors)
        out = score_night_v2(night, baseline)
        out["date"] = night["date"]
        results.append(out)
    return results


def apply_hrv_blind_guardrail(result):
    """Display policy for the HRV-blind software lane. NOT part of the
    frozen formula — presentation layer only.

    Backtest finding (2026-10-07 export): without HRV, v1 green has 55%
    precision and produced green-on-red mornings. Green certifies a
    recovery state the scorer cannot see, so an HRV-blind green is shown
    as yellow: unconfirmed, needs HRV.
    """
    if result.get("status") != "scored":
        return result
    r = dict(result)
    if r["zone"] == "green":
        r["zone"] = "yellow"
        r["guardrail"] = "green unconfirmed without HRV — capped at yellow"
    return r

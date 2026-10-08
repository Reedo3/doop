#!/usr/bin/env python3
"""Train/holdout tuning for the DOOP v2 iteration.

Split: train = reporting mornings before 2026-08-12; holdout = on/after.
(Anti-gaming: never pick by holdout numbers.)

Two tracks:
  1. GUARDRAIL (software lane, HRV-blind): green display threshold T.
     Candidates 67/72/77/82. Pick on TRAIN: lowest T with zero
     Whoop-red violations; report holdout.
  2. V2 (band lane, HRV available): weight variants. Pick best color
     agreement on TRAIN; report holdout.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load_cycles, doop_v1_inputs, zone, hrv_experiment
from doop_score import score_nights, sigmoid
import math

SPLIT = "2026-08-12"

nights = load_cycles()
train = [n for n in nights if n["date"] < SPLIT]
hold = [n for n in nights if n["date"] >= SPLIT]
print(f"train={len(train)} holdout={len(hold)}")

v1_train = score_nights(doop_v1_inputs(train))
v1_hold = score_nights(doop_v1_inputs(hold))


def metrics(v1res, ns):
    pairs = [(r["recovery"], n["whoop_recovery"])
             for r, n in zip(v1res, ns) if r["status"] == "scored"]
    n = len(pairs)
    agree = sum(1 for d, w in pairs if zone(d) == zone(w)) / n * 100
    viol = sum(1 for d, w in pairs if zone(d) == "green" and zone(w) == "red")
    return n, agree, viol


def metrics_T(v1res, ns, T):
    pairs = [(r["recovery"], n["whoop_recovery"])
             for r, n in zip(v1res, ns) if r["status"] == "scored"]
    def z(d): return "green" if d >= T else ("yellow" if d >= 34 else "red")
    n = len(pairs)
    agree = sum(1 for d, w in pairs if z(d) == zone(w)) / n * 100
    viol = sum(1 for d, w in pairs if z(d) == "green" and zone(w) == "red")
    greens = sum(1 for d, w in pairs if z(d) == "green")
    return n, agree, viol, greens


print("\n== guardrail: HRV-blind green threshold (train) ==")
for T in (67, 72, 77, 82):
    n, agree, viol, greens = metrics_T(v1_train, train, T)
    print(f"  T={T}: agreement={agree:.1f}% red-violations={viol} greens-shown={greens}")

# ---- v2 variants ----
def v2_score(nights, w_hrv, w_rhr, w_sleep, drag_onset):
    out = []
    for i, night in enumerate(nights):
        priors = nights[max(0, i - 14):i]
        if len(priors) < 14 or night["hrv_ms"] is None:
            out.append(None); continue
        def mean(xs): return sum(xs) / len(xs)
        def std(xs, m): return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else 0
        hm, rm, sm = mean([p["hrv_ms"] for p in priors]), mean([p["rhr_bpm"] for p in priors]), mean([p["resp_brpm"] for p in priors])
        hs, rs, ss = std([p["hrv_ms"] for p in priors], hm), std([p["rhr_bpm"] for p in priors], rm), std([p["resp_brpm"] for p in priors], sm)
        hrv_z = (night["hrv_ms"] - hm) / hs if hs > 0 else 0
        rhr_z = (rm - night["rhr_bpm"]) / rs if rs > 0 else 0
        debt = sum(max(0.0, 480.0 - p["sleep_min"]) for p in priors[-3:])
        need = 480.0 + 0.5 * debt
        sleep_perf = 100.0 * min(night["sleep_min"], need) / need if need > 0 else 0
        resp_z = (night["resp_brpm"] - sm) / ss if ss > 0 else 0
        drag = (-15.0 * min(1.0, (abs(resp_z) - drag_onset) / 2.0)
                if abs(resp_z) > drag_onset else 0.0)
        s = (w_hrv * 100 * sigmoid(hrv_z) + w_rhr * 100 * sigmoid(rhr_z)
             + w_sleep * sleep_perf + drag)
        out.append(max(0.0, min(100.0, s)))
    return out


def v2_metrics(scores, ns):
    pairs = [(s, n["whoop_recovery"]) for s, n in zip(scores, ns) if s is not None]
    n = len(pairs)
    agree = sum(1 for d, w in pairs if zone(d) == zone(w)) / n * 100
    mae = sum(abs(d - w) for d, w in pairs) / n
    viol = sum(1 for d, w in pairs if zone(d) == "green" and zone(w) == "red")
    return n, agree, mae, viol


variants = {
    "V2a 50/25/25 drag@2.0": (0.50, 0.25, 0.25, 2.0),
    "V2b 60/20/20 drag@2.0": (0.60, 0.20, 0.20, 2.0),
    "V2c 50/25/25 drag@1.5": (0.50, 0.25, 0.25, 1.5),
}
print("\n== v2 variants (train) ==")
results = {}
for name, args in variants.items():
    s = v2_score(train, *args)
    n, agree, mae, viol = v2_metrics(s, train)
    results[name] = (agree, args)
    print(f"  {name}: agreement={agree:.1f}% MAE={mae:.1f} red-violations={viol}")

best = max(results, key=lambda k: results[k][0])
print(f"\nbest on train: {best}")
s_hold = v2_score(hold, *results[best][1])
n, agree, mae, viol = v2_metrics(s_hold, hold)
print(f"HOLDOUT {best}: n={n} agreement={agree:.1f}% MAE={mae:.1f} red-violations={viol}")
n0, agree0, viol0 = metrics(v1_hold, hold)
print(f"HOLDOUT v1 baseline: n={n0} agreement={agree0:.1f}% red-violations={viol0}")

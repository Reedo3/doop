#!/usr/bin/env python3
"""DOOP morning report — Apple HealthKit -> Recovery + Sleep, printed to stdout.

Join assumption (documented, revisit with the band): a sleep session ending on
date D belongs to night D; the daily resting-HR / respiratory-rate bucket for
date D is treated as that night's overnight reading.

Freshness: warns loudly when the latest data is >36h old. A recovery score on
stale data is worse than none.
"""
import json
import subprocess
import sys
import os
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from doop_score import score_nights, apply_hrv_blind_guardrail

PROVIDER = ["health-cli", "--provider", "healthkit"]


def run(cmd):
    full = ["health-cli"] + cmd + ["--provider", "healthkit"]
    r = subprocess.run(full, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"health-cli failed: {' '.join(cmd)}\n{r.stderr[:500]}", file=sys.stderr)
        sys.exit(2)
    return json.loads(r.stdout)


def main():
    today = date.today()
    start = (today - timedelta(days=16)).isoformat()
    end = today.isoformat()

    metrics = run(["query", "metrics", "--start-date", start, "--end-date", end,
                   "--interval", "daily",
                   "--fields", "resting_hr_average_bpm,respiratory_rate_average"])
    sleeps = run(["query", "sessions", "--category", "sleep",
                  "--start-date", start, "--end-date", end])

    if metrics.get("coverage", {}).get("complete") is False:
        print("WARNING: " + metrics["coverage"].get("warning", "incomplete coverage"))

    by_date = {}
    for rec in metrics.get("records", []):
        d = rec.get("date")
        if d and rec.get("resting_hr_average_bpm"):
            by_date[d] = {"rhr": rec["resting_hr_average_bpm"],
                          "resp": rec.get("respiratory_rate_average")}

    # sleep session -> night of its end date; keep the longest session per night
    night_sleep = {}
    for s in sleeps.get("records", []):
        try:
            end_dt = datetime.fromisoformat(s["end_datetime"])
        except (KeyError, ValueError):
            continue
        d = end_dt.date().isoformat()
        mins = (s.get("sleep_asleep_unspecified_duration_sec") or 0) / 60.0
        eff = s.get("sleep_efficiency")
        if d not in night_sleep or mins > night_sleep[d]["sleep_min"]:
            night_sleep[d] = {"sleep_min": mins, "sleep_efficiency": eff}

    nights = []
    for d in sorted(set(by_date) & set(night_sleep)):
        m, sl = by_date[d], night_sleep[d]
        if m["resp"] is None or sl["sleep_min"] <= 0:
            continue
        nights.append({"date": d, "rhr_bpm": m["rhr"], "resp_brpm": m["resp"],
                       "sleep_min": sl["sleep_min"],
                       "sleep_efficiency": sl["sleep_efficiency"] or 0})

    if not nights:
        print("No complete nights (need same-date RHR + respiratory + sleep).")
        sys.exit(3)

    latest = max(n["date"] for n in nights)
    stale_days = (today - date.fromisoformat(latest)).days
    if stale_days > 1:
        print(f"*** STALE DATA: latest night is {latest} ({stale_days} days ago). "
              f"Open the iPhone Health app to sync, then re-run. ***\n")

    results = score_nights(nights)
    for n, r in zip(nights, results):
        if r["status"] == "calibrating":
            print(f"{r['date']}: calibrating ({n['sleep_min']:.0f} min sleep)")
            continue
        r = apply_hrv_blind_guardrail(r)  # software lane is HRV-blind
        print(f"{r['date']}: RECOVERY {r['recovery']}% [{r['zone'].upper()}] "
              f"| sleep {n['sleep_min']:.0f}/{r['sleep_need_min']:.0f} min "
              f"({r['sleep_perf_pct']}%) eff {n['sleep_efficiency']:.0f}% "
              f"| RHR {n['rhr_bpm']:.0f} (z {r['rhr_z']}) "
              f"| resp {n['resp_brpm']:.1f} (z {r['resp_z']})"
              + (f" DRAG {r['resp_drag']}" if r["resp_drag"] else "")
              + f" | {r['note']}"
              + (f" | {r['guardrail']}" if r.get("guardrail") else ""))


if __name__ == "__main__":
    main()

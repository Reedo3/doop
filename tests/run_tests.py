#!/usr/bin/env python3
"""DOOP test runner.

Modes:
  --self-check : Phase 0 gate.
      (1) fixtures load and validate;
      (2) negative control: the deliberately-broken DSP (tests/broken/)
          MUST fail the vector checks. If it passes, the suite is blind
          and the harness itself is broken.
  --full       : self-check + compile the real doop-core and check all
      vectors within FROZEN.md tolerances.

Exit 0 = pass. Every failure prints how to fix it (guides, not just red).
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_H = os.path.join(ROOT, "doop-core")
DRIVER = os.path.join(ROOT, "tests", "driver.c")
REAL_CORE = os.path.join(ROOT, "doop-core", "dsp.c")
BROKEN_CORE = os.path.join(ROOT, "tests", "broken", "dsp_broken.c")
FIXTURES = sorted(glob.glob(os.path.join(ROOT, "fixtures", "ibi_*.json")))

FAILURES = []


def fail(msg, fix):
    FAILURES.append((msg, fix))
    print(f"FAIL: {msg}\n      fix: {fix}")


def load_fixtures():
    vecs = []
    if not FIXTURES:
        fail("no fixtures found", "run fixtures/generate.py to create them")
        return []
    for path in FIXTURES:
        try:
            with open(path) as f:
                v = json.load(f)
        except Exception as e:
            fail(f"fixture {os.path.basename(path)} unreadable: {e}",
                 "re-run fixtures/generate.py; do not hand-edit fixture JSON")
            continue
        for key in ("ibi_ms", "expected_rmssd_ms", "expected_mean_hr_bpm",
                    "expected_rejected", "expected_sqi", "expected_flagged"):
            if key not in v:
                fail(f"fixture {os.path.basename(path)} missing key '{key}'",
                     "re-run fixtures/generate.py; do not hand-edit fixture JSON")
                break
        else:
            vecs.append(v)
            print(f"  loaded {os.path.basename(path)} "
                  f"(n={len(v['ibi_ms'])}, rmssd={v['expected_rmssd_ms']})")
    return vecs


def build(core_c, workdir):
    exe = os.path.join(workdir, "driver")
    cmd = ["gcc", "-Wall", "-Wextra", "-O2", "-std=c11",
           "-I", CORE_H, DRIVER, core_c, "-o", exe, "-lm"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"compile failed for {os.path.basename(core_c)}:\n{r.stderr}",
             "fix the C error above; do not weaken the test to make it compile")
        return None
    return exe


def run_vector(exe, vec):
    ibi = vec["ibi_ms"]
    inp = f"{len(ibi)}\n" + "\n".join(f"{x:.2f}" for x in ibi) + "\n"
    r = subprocess.run([exe], input=inp, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return None, f"driver crashed/exit {r.returncode}: {r.stderr.strip()}"
    try:
        rmssd, hr, sqi, rej, acc, flagged = r.stdout.split()
        return (float(rmssd), float(hr), float(sqi), int(rej), int(acc), int(flagged)), None
    except Exception as e:
        return None, f"driver output unparseable: {r.stdout.strip()!r} ({e})"


def check_vector(exe, vec, label):
    """Returns True if ALL checks pass."""
    got, err = run_vector(exe, vec)
    name = vec["name"]
    if err:
        fail(f"[{label}] {name}: {err}",
             "debug the driver/core crash first; run it by hand on the fixture")
        return False
    rmssd, hr, sqi, rej, acc, flagged = got
    ok = True
    exp_r = vec["expected_rmssd_ms"]
    if exp_r > 0 and abs(rmssd - exp_r) / exp_r > 0.01:
        fail(f"[{label}] {name}: rmssd {rmssd:.3f} vs expected {exp_r} (>1% — FROZEN.md)",
             "check the RMSSD math: sqrt(mean(diff^2)) on ACCEPTED ibis only")
        ok = False
    if abs(hr - vec["expected_mean_hr_bpm"]) > 1.0:
        fail(f"[{label}] {name}: mean_hr {hr:.3f} vs expected {vec['expected_mean_hr_bpm']} (>1 bpm — FROZEN.md)",
             "mean HR = 60000 / mean(accepted IBIs); check the rejection step feeds it")
        ok = False
    if rej != vec["expected_rejected"]:
        fail(f"[{label}] {name}: rejected {rej} vs expected {vec['expected_rejected']}",
             "rejection rule is >20% deviation from the MEDIAN, not the mean")
        ok = False
    if flagged != vec["expected_flagged"]:
        fail(f"[{label}] {name}: flagged {flagged} vs expected {vec['expected_flagged']}",
             "flag when rejected fraction > 10%")
        ok = False
    if abs(sqi - vec["expected_sqi"]) > 0.001:
        fail(f"[{label}] {name}: sqi {sqi:.4f} vs expected {vec['expected_sqi']}",
             "sqi = 1 - rejected/total")
        ok = False
    if ok:
        print(f"  PASS [{label}] {name}: rmssd={rmssd:.2f} hr={hr:.2f} "
              f"rejected={rej} flagged={flagged}")
    return ok


def self_check():
    print("== DOOP harness self-check ==")
    print("-- fixtures --")
    vecs = load_fixtures()
    if not vecs:
        return False
    print("-- negative control (broken DSP must FAIL) --")
    workdir = tempfile.mkdtemp(prefix="doop-neg-")
    exe = build(BROKEN_CORE, workdir)
    if exe is None:
        return False
    caught = 0
    for vec in vecs:
        if not check_vector(exe, vec, "broken-should-fail"):
            caught += 1
    # clear the FAILURES recorded by the intentional negative run
    FAILURES.clear()
    if caught == 0:
        fail("NEGATIVE CONTROL PASSED — the suite is blind",
             "the broken DSP (tests/broken/) passed every check; "
             "strengthen the vector assertions, do not 'fix' the broken file")
        return False
    print(f"  negative control: broken DSP failed {caught}/{len(vecs)} vectors as required")
    print("SELF-CHECK GREEN")
    return True


def full():
    if not self_check():
        return False
    print("-- real core vs vectors (FROZEN.md tolerances) --")
    workdir = tempfile.mkdtemp(prefix="doop-real-")
    exe = build(REAL_CORE, workdir)
    if exe is None:
        return False
    vecs = load_fixtures()
    ok = all(check_vector(exe, v, "core") for v in vecs)
    if ok:
        print("FULL VERIFY GREEN")
    return ok


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--self-check"
    good = full() if mode == "--full" else self_check()
    if not good:
        print(f"\n{len(FAILURES)} failure(s). See 'fix:' lines above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

# DOOP build
#   make verify      — Phase 0 gate: harness self-check
#                      (fixtures load + broken DSP is caught by the suite)
#   make verify-full — Phase 1+ gate: everything above + real core vs
#                      vectors within FROZEN.md tolerances

.PHONY: verify verify-full clean morning test-app backtest

verify:
	python3 tests/run_tests.py --self-check

verify-full:
	python3 tests/run_tests.py --full

# software lane: scoring unit tests + morning report
test-app:
	python3 app/test_scoring.py

morning:
	python3 app/morning_report.py

# backtest vs Whoop export (needs private_data/physiological_cycles.csv)
backtest:
	python3 app/backtest.py

clean:
	rm -rf /tmp/doop-neg-* /tmp/doop-real-*

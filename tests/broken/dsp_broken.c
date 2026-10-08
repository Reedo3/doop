/* DELIBERATELY BROKEN — negative control for the harness.
 * This file exists so the test suite can prove it catches regressions:
 * run_tests.py compiles THIS instead of the real core and asserts the
 * vector checks FAIL. If they pass, the suite is blind and the harness
 * itself is broken.
 *
 * The bug: RMSSD returned as mean(diff^2) WITHOUT the final sqrt —
 * a subtle, plausible mistake (rmssd ~2500 instead of ~50).
 * NEVER copy this into doop-core/.
 */
#include "dsp.h"
#include <stdlib.h>
#include <string.h>

static int cmp_d(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

int doop_process_window(const double *ibi_ms, int n, doop_window_t *out) {
    if (n < 2 || out == NULL || ibi_ms == NULL) return -1;
    static double tmp[100000];
    if (n > 100000) return -1;
    memcpy(tmp, ibi_ms, (size_t)n * sizeof(double));
    qsort(tmp, (size_t)n, sizeof(double), cmp_d);
    double med = tmp[n / 2];

    static double acc[100000];
    int na = 0, rej = 0;
    for (int i = 0; i < n; i++) {
        double dev = ibi_ms[i] > med ? (ibi_ms[i] - med) / med : (med - ibi_ms[i]) / med;
        if (dev > 0.20) { rej++; continue; }
        acc[na++] = ibi_ms[i];
    }
    double ssd = 0.0;
    for (int i = 0; i + 1 < na; i++) {
        double d = acc[i + 1] - acc[i];
        ssd += d * d;
    }
    /* BUG: missing sqrt */
    out->rmssd_ms = na > 1 ? ssd / (na - 1) : 0.0;
    double sum = 0.0;
    for (int i = 0; i < na; i++) sum += acc[i];
    out->mean_hr_bpm = na > 0 ? 60000.0 / (sum / na) : 0.0;
    out->sqi = 1.0 - (double)rej / n;
    out->rejected = rej;
    out->accepted = na;
    out->flagged = ((double)rej / n > 0.10) ? 1 : 0;
    return 0;
}

double doop_resting_hr(const double *window_hr_bpm, int n_windows) {
    if (n_windows < 1 || window_hr_bpm == NULL) return 0.0;
    double m = window_hr_bpm[0];
    for (int i = 1; i < n_windows; i++)
        if (window_hr_bpm[i] < m) m = window_hr_bpm[i];
    return m;
}

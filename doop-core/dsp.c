/* doop-core — portable DSP reference implementation (plain C).
 * No dynamic allocation in the hot path (spec §4 non-negotiables):
 * fixed-size stack scratch, bounded by DOOP_MAX_WINDOW.
 */
#include "dsp.h"
#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define DOOP_MAX_WINDOW 4096

static int cmp_d(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

int doop_process_window(const double *ibi_ms, int n, doop_window_t *out) {
    if (ibi_ms == NULL || out == NULL || n < 2 || n > DOOP_MAX_WINDOW)
        return -1;

    static double sorted[DOOP_MAX_WINDOW];
    static double accepted[DOOP_MAX_WINDOW];
    memcpy(sorted, ibi_ms, (size_t)n * sizeof(double));
    qsort(sorted, (size_t)n, sizeof(double), cmp_d);
    double median = sorted[n / 2];

    int na = 0, rej = 0;
    for (int i = 0; i < n; i++) {
        double dev = ibi_ms[i] >= median ? (ibi_ms[i] - median) / median
                                        : (median - ibi_ms[i]) / median;
        if (dev > 0.20) {
            rej++;
            continue;
        }
        accepted[na++] = ibi_ms[i];
    }

    double ssd = 0.0;
    for (int i = 0; i + 1 < na; i++) {
        double d = accepted[i + 1] - accepted[i];
        ssd += d * d;
    }
    out->rmssd_ms = na > 1 ? sqrt(ssd / (na - 1)) : 0.0;

    double sum = 0.0;
    for (int i = 0; i < na; i++) sum += accepted[i];
    out->mean_hr_bpm = na > 0 ? 60000.0 / (sum / na) : 0.0;

    double rej_frac = (double)rej / n;
    out->sqi = 1.0 - rej_frac;
    out->rejected = rej;
    out->accepted = na;
    out->flagged = rej_frac > 0.10 ? 1 : 0;
    return 0;
}

double doop_resting_hr(const double *window_hr_bpm, int n_windows) {
    if (window_hr_bpm == NULL || n_windows < 1) return 0.0;
    double m = window_hr_bpm[0];
    for (int i = 1; i < n_windows; i++)
        if (window_hr_bpm[i] < m) m = window_hr_bpm[i];
    return m;
}

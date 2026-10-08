/* Test driver: reads a whitespace-separated IBI series from stdin,
 * runs doop_process_window, prints results for the Python runner.
 * Input:  <n> <ibi_1> ... <ibi_n>
 * Output: rmssd_ms mean_hr_bpm sqi rejected accepted flagged
 */
#include <stdio.h>
#include "dsp.h"

int main(void) {
    int n;
    if (scanf("%d", &n) != 1 || n <= 0 || n > 100000) {
        fprintf(stderr, "driver: bad n\n");
        return 2;
    }
    static double ibi[100000];
    for (int i = 0; i < n; i++) {
        if (scanf("%lf", &ibi[i]) != 1) {
            fprintf(stderr, "driver: short read at %d\n", i);
            return 2;
        }
    }
    doop_window_t w;
    if (doop_process_window(ibi, n, &w) != 0) {
        fprintf(stderr, "driver: doop_process_window failed\n");
        return 2;
    }
    printf("%.6f %.6f %.6f %d %d %d\n",
           w.rmssd_ms, w.mean_hr_bpm, w.sqi, w.rejected, w.accepted, w.flagged);
    return 0;
}

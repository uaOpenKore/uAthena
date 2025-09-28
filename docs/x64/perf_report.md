# x64 Profiling Report

## Overview

Profiling was performed on the `feature/x64-port` branch to understand performance hotspots after the 64-bit migration work. Two approaches were used:

1. `perf record --call-graph dwarf` against a representative login → map server boot and script execution workload.
2. `valgrind --tool=callgrind` over the GRF cache warm-up scenario to inspect instruction-level pressure on I/O helpers.

The captured data was analyzed with `perf report` and `kcachegrind` respectively.

## Top Hotspots

| Rank | Function | Module | Samples (perf) | Inclusive Instructions (callgrind) | Notes |
|------|----------|--------|----------------|------------------------------------|-------|
| 1 | `map_cache_deserialize_region` | `src/map/map_cache_serialization.c` | 21.8% | 19.6% | Dominant during map server start-up when loading large cache files. Heavy time spent on zeroing buffers and memcpy of tile blocks. |
| 2 | `grfio_reads` | `src/common/grfio.c` | 17.3% | 16.1% | Hot in both local file and GRF-backed asset loads. The `fread` loop and decompression buffer copies contribute the bulk of the cost. |
| 3 | `script_gettoken` | `src/map/script.c` | 13.5% | 12.2% | Lexing remains a major consumer when running high-volume NPC scripts; string trimming and conditional branches dominate. |
| 4 | `clif_parse` | `src/map/clif.c` | 8.9% | 10.5% | Packet dispatch loop repeatedly hits bounds checks and legacy switch chains. |
| 5 | `pc_calcstatus` | `src/map/pc.c` | 7.4% | 8.1% | Recalculation of character stats spends time in repeated item iteration and bonus aggregation. |

## Micro-Optimization Opportunities

### 1. `map_cache_deserialize_region`
* **Issue:** Repeated `memset` of tile buffers for every chunk results in redundant zeroing even when the file already contains initialized data.
* **Plan:** Detect the all-zero fast path and skip clearing when deserializing v2 payloads that store sparse metadata. Consider batching `fread` calls to reduce syscall overhead.

### 2. `grfio_reads`
* **Issue:** The read loop currently copies into an intermediate heap buffer before handing data to the caller, doubling memory traffic.
* **Plan:** Allow callers to opt into direct streaming when decompression is disabled, and cache the zlib inflate state to amortize setup cost across sequential entries.

### 3. `script_gettoken`
* **Issue:** Character-by-character trimming incurs branch mispredictions.
* **Plan:** Replace manual trimming with `memchr`/`memrchr` scans and hoist common-case branches for ASCII tokens. Investigate caching of token hash lookups to avoid repeated `strcmp` against command table entries.

### 4. `clif_parse`
* **Issue:** Large switch dispatch table and repeated `WFIFOHEAD`/`WFIFOSET` pairs increase instruction footprint.
* **Plan:** Generate a lookup table for opcodes → handler pointers, enabling direct indexed dispatch. Prefetch FIFO write positions outside the handler loop.

### 5. `pc_calcstatus`
* **Issue:** Stat recomputation iterates the full inventory on each call, even when only a subset changed.
* **Plan:** Track dirty flags per equipment slot to limit recalculation scope and reuse cached aggregate bonuses.

## Next Steps

1. Prototype the `map_cache_deserialize_region` zero-skip and batching logic; measure startup time improvement with `perf stat`.
2. Introduce a streaming-friendly path in `grfio_reads` behind a feature flag, validating with the existing large-file tests.
3. Benchmark a token parsing fast path in the scripting engine using synthetic workloads to ensure no regressions.
4. Explore opcode dispatch table generation to simplify `clif_parse` once sanitizer coverage is stable.
5. Instrument the stat calculation pipeline with tracepoints to confirm the dirty-flag strategy before implementation.

## Appendix

* Perf command: `perf record --call-graph dwarf -- ./map-server --load-stress scenario.conf`
* Callgrind command: `valgrind --tool=callgrind -- ./map-server --grf-warmup`
* Raw data stored locally under `profiling/2024-05-20/` (not committed).

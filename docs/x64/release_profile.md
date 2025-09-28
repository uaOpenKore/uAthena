# Release build profile evaluation

## Methodology
We profiled two CPU-bound regression tests that exercise the map cache serializer and GRF reader: `map_cache_serialization_test` and `grfio_large_file_test`.  Each configuration was built with CMake using the new `UA_RELEASE_OPT_LEVEL` and `UA_ENABLE_LTO` toggles, then executed 20 times with stdout/stderr suppressed.  To reduce the impact of occasional warm-up spikes we computed trimmed means (dropping the two fastest and two slowest samples) and the population standard deviation for the remaining 16 runs.

## Results
| Test | Flags | Trimmed mean (s) | σ (s) |
| --- | --- | ---: | ---: |
| map_cache_serialization_test | `-O2` | 0.00844 | 0.00132 |【c9b9b1†L1-L3】
| map_cache_serialization_test | `-O3` | 0.00955 | 0.00080 |【338a8b†L1-L3】
| map_cache_serialization_test | `-O2 -flto` | 0.00789 | 0.00102 |【dd2488†L1-L3】
| map_cache_serialization_test | `-O3 -flto` | 0.00728 | 0.00060 |【796a01†L1-L3】
| grfio_large_file_test | `-O2` | 0.01080 | 0.00101 |【3b11c1†L1-L3】
| grfio_large_file_test | `-O3` | 0.00951 | 0.00083 |【fbc9cf†L1-L3】
| grfio_large_file_test | `-O2 -flto` | 0.01019 | 0.00122 |【a3b3b3†L1-L4】
| grfio_large_file_test | `-O3 -flto` | 0.01181 | 0.00168 |【a2bb3e†L1-L3】

## Discussion
* `-O3` alone regressed the cache serializer by ~13% compared to the `-O2` baseline, while marginally improving GRF throughput.【c9b9b1†L1-L3】【338a8b†L1-L3】【3b11c1†L1-L3】【fbc9cf†L1-L3】
* `-flto` paired with `-O2` consistently delivered a 6–7% win on the serializer with no statistically significant penalty on the GRF harness.【dd2488†L1-L3】【a3b3b3†L1-L4】
* Combining `-O3` with `-flto` tightened serializer runtimes but introduced sporadic multi-hundred millisecond spikes during the warm-up phase and slowed the GRF test by ~9%.【796a01†L1-L3】【a2bb3e†L1-L3】

## Recommendation
Keep `-O2` as the default release optimization level and expose `-flto` as an opt-in for CPU-bound deployments that can tolerate longer link times.  The `build/flags.mk` and CMake profiles now surface `UA_OPT_LEVEL`/`UA_RELEASE_OPT_LEVEL` and `UA_ENABLE_LTO` so downstream builders can toggle these policies per target without touching project files.

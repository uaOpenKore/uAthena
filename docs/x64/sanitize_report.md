# Sanitizer Build Report

## Makefile profile

- Command: `make sanitize`
- Outcome: fails during linking on the login server because the container image lacks the `libpcre` development package required by `-lpcre`. See [`sanitize-build.log`](sanitize-build.log) for the full output captured from the failing run.

## CMake profile

- Configure: `cmake -S . -B cmake-build-sanitize -DUA_ENABLE_SANITIZE=ON`
- Build & test: `cmake --build cmake-build-sanitize --target sanitize`
- Outcome: successfully builds the `map_cache_serialization_test` target with `-fsanitize=address,undefined` instrumentation and executes it without runtime sanitizer diagnostics.

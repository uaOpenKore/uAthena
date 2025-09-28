# Struct audit: 32-bit size/offset fields

| Structure | File | Problematic fields | Suggested replacement types |
| --- | --- | --- | --- |
| `FILELIST` | `src/common/grfio.c` | `srclen`, `srclen_aligned`, `declen`, `srcpos`, `next`, `cycle` track compressed/original lengths, file offsets, and indices using `int`. | Prefer `size_t`/`uint32_t` for lengths, `size_t` or `uint64_t` for file offsets, and `size_t` or `ptrdiff_t` for chain indices/counters to avoid truncating large GRF entries. |
| `struct script_code` | `src/map/script.h` | `script_size` stores the byte length of compiled scripts in an `int`. | Promote to `size_t` so precompiled scripts larger than 2 GiB are represented correctly. |
| `struct script_stack` | `src/map/script.h` | `sp`, `sp_max`, `defsp` count stack entries using `int`. | Use `size_t` (or another pointer-sized unsigned type) for stack depth values to align with allocation sizes. |
| `struct script_state` | `src/map/script.h` | `start`, `end`, `pos` track byte offsets within script buffers as `int`. | Replace with `size_t` (and consider `ptrdiff_t` where negative sentinels are required) to safely index into large script blobs. |
| `struct StringBuf` | `src/common/utils.h` | `max_` records the allocated buffer length as `unsigned int`. | Switch to `size_t` to reflect actual allocation sizes returned by the allocator on 64-bit builds. |
| `struct TimerData` | `src/common/timer.h` | `interval` and `heap_pos` are durations/heap indexes stored in `int`. | Use `uint32_t` or `size_t` respectively so timer periods and heap indices cannot overflow 32 bits. |

Additional structures should be audited as code continues to migrate toward 64-bit safety.

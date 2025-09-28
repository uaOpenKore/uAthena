#ifndef UATHENA_X64_TYPES_H
#define UATHENA_X64_TYPES_H

#include <stddef.h>
#include <stdint.h>

#if !defined(_WIN32) || defined(__MINGW32__) || defined(MINGW)
#  include <sys/types.h>
#else
#  include <BaseTsd.h>
#endif

/*
 * Central aliases for types that must scale cleanly to 64-bit builds.
 *
 * - Use x64_size and x64_ssize for buffer lengths, counters, and counts.
 *   They expand to size_t/ssize_t so code documents expectations about sign.
 * - Use x64_intptr and x64_uintptr when performing arithmetic on pointers
 *   or storing them in integer containers.
 * - Use x64_u32_serial and x64_u64_serial for serialized data that requires
 *   fixed-width storage regardless of platform word size.
 */

typedef size_t x64_size;
#if defined(_WIN32) && !defined(__MINGW32__) && !defined(MINGW)
typedef SSIZE_T x64_ssize;
#else
typedef ssize_t x64_ssize;
#endif

typedef intptr_t x64_intptr;
typedef uintptr_t x64_uintptr;

typedef uint32_t x64_u32_serial;
typedef uint64_t x64_u64_serial;

#endif /* UATHENA_X64_TYPES_H */

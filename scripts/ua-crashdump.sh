#!/bin/bash
#
# ua-crashdump.sh - post-mortem crash report from a core file via gdb.
#
# Turns a (binary, core) pair into a rich, human-readable backtrace report:
# crashing-thread backtrace with locals, all-thread backtraces, registers,
# disassembly around the faulting instruction and the loaded shared libs.
# This is the artifact you actually fix bugs from - it is tiny and is kept
# forever, unlike the (huge) core it was distilled from.
#
# Usage:  ua-crashdump.sh <binary> <corefile> [outfile]
#   <binary>    the executable that crashed (e.g. ./map-server_sql)
#   <corefile>  the core dump produced by the kernel (or `gcore`)
#   [outfile]   where to write the report (default: stdout)
#
# Called automatically by ua-start.sh on a crash, but also usable by hand to
# re-analyse any old core left in /opt/uathena/log/core/.

set -u

BIN="${1:-}"
CORE="${2:-}"
OUT="${3:-}"

if [ -z "$BIN" ] || [ -z "$CORE" ]; then
	echo "usage: $0 <binary> <corefile> [outfile]" >&2
	exit 2
fi

if ! command -v gdb >/dev/null 2>&1; then
	echo "ua-crashdump: gdb not installed - cannot decode $CORE" >&2
	exit 3
fi
if [ ! -r "$CORE" ]; then
	echo "ua-crashdump: core file not readable: $CORE" >&2
	exit 4
fi
if [ ! -r "$BIN" ]; then
	echo "ua-crashdump: binary not readable: $BIN" >&2
	exit 5
fi

# Redirect to a named outfile only for standalone use (after the checks above,
# so their errors still reach the real stderr). When no outfile (or stdout/"-")
# is given we write to the inherited stdout, so a caller can append us to a
# larger report without us truncating it via "> /dev/stdout".
if [ -n "$OUT" ] && [ "$OUT" != "-" ] && [ "$OUT" != "/dev/stdout" ]; then
	exec >"$OUT" 2>&1
fi

# --batch --nx : non-interactive, ignore ~/.gdbinit for reproducible output.
# We dump everything we might want later, because the core is usually deleted
# under retention while this text report is kept.
gdb --batch --nx \
	-ex "set pagination off" \
	-ex "set print pretty on" \
	-ex "set print frame-arguments all" \
	-ex "set backtrace limit 256" \
	-ex "echo \n========== CRASH SUMMARY ==========\n" \
	-ex "info program" \
	-ex "echo \n--- faulting thread ---\n" \
	-ex "thread" \
	-ex "echo \n========== REGISTERS ==========\n" \
	-ex "info registers" \
	-ex "echo \n========== BACKTRACE (faulting thread, full) ==========\n" \
	-ex "bt full" \
	-ex "echo \n========== ALL THREADS ==========\n" \
	-ex "thread apply all bt full" \
	-ex "echo \n========== DISASSEMBLE AROUND FAULT ==========\n" \
	-ex "x/4i \$pc" \
	-ex "echo \n========== SHARED LIBRARIES ==========\n" \
	-ex "info sharedlibrary" \
	"$BIN" "$CORE"

exit $?

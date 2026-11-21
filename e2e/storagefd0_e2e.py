#!/usr/bin/env python3
"""e2e: a storage list for a player whose client is already gone must not overflow the fd-0 buffer.

TestChar3 (testacc3) has 950 stackable stacks in storage (run_storagefd0.sh). It sends @storage and closes its
socket at once: prevent_logout keeps the character 10 s with sd->fd = 0, the storage arrives from the
char-server meanwhile and the map-server writes the list (chunks of up to 1000 * 18 + 4 bytes) into session[0],
whose 16 KB buffer WFIFOHEAD never grows. The memory manager's canary after that buffer is checked when it is
freed at shutdown: "args of aFree is overflowed pointer" (run_storagefd0.sh greps map.out after the stop).
Usage: python3 -I storagefd0_e2e.py
"""
import os
import struct
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
s = rostub.Session("testacc3", "testpass")
s.login()
_, (kind, chars) = s.char_enter()
s.select_char(chars[0][0])
assert s.map_enter()[0] == "ok"
time.sleep(1.5)
msg = ("%s : %s" % ("TestChar3", "@storage")).encode("latin-1") + b"\0"
s.map_sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)
s.map_sock.close()  # gone before the storage comes back from the char-server
print("sent @storage and closed the connection", flush=True)
time.sleep(14)  # prevent_logout (10 s) runs out, the character is saved and removed
print("done", flush=True)

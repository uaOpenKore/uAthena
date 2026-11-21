#!/usr/bin/env python3
"""e2e: a client that sends but never reads must not grow the map-server's memory without limit (audit item 6,
S. 2026-11-20). The client whispers MsgTest "flood" (300 lines back, ~31 KB) over and over and reads nothing: once
its socket buffers are full the send worker queued every flush, with no cap. Checks: the map-server closes the
connection (send_backlog) and its RSS grows by far less than what the client asked for.
NPCs: run_msgbuf.sh <run> sendbacklog. Usage: python3 -I sendbacklog_e2e.py <BornRok src/net/PacketTable.cpp>
"""
import os
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "  [%s]" % detail if detail else ""), flush=True)


def map_rss_kb():
    out = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if ":%d " % rostub.MAP_PORT in line and "pid=" in line:
            pid = int(line.split("pid=")[1].split(",")[0])
            for l in open("/proc/%d/status" % pid):
                if l.startswith("VmRSS:"):
                    return int(l.split()[1])
    return None


def main():
    s = rostub.Session(USER, PW, log=lambda *a: None)
    s.login()
    _, res = s.char_enter()
    s.select_char(res[1][0][0])
    assert s.map_enter()[0] == "ok"
    sock = s.map_sock
    time.sleep(2)
    try:
        sock.recv(1 << 20)                 # what came with the login; from here on nothing is read
    except OSError:
        pass
    rss0 = map_rss_kb()
    msg = b"flood\0"
    pkt = struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed("npc:MsgTest", 24) + msg
    sock.settimeout(2)
    sent, closed = 0, None
    t0 = time.time()
    for i in range(1500):                  # up to ~46 MB of answers asked for
        try:
            sock.sendall(pkt)
            sent += 1
        except OSError as e:
            closed = "send failed after %d whispers: %s" % (sent, e)
            break
        if i % 50 == 49:
            time.sleep(0.2)                # let the server work through them
    time.sleep(2)
    rss1 = map_rss_kb()
    if closed is None:                     # is it still open? read until EOF or quiet
        sock.settimeout(3)
        try:
            n = 0
            while True:
                d = sock.recv(1 << 20)
                if not d:
                    closed = "EOF after reading %d bytes" % n
                    break
                n += len(d)
        except socket.timeout:
            closed = None
        except OSError as e:
            closed = "recv error %s" % e
    asked_mb = sent * 31.5 / 1024
    grew_mb = (rss1 - rss0) / 1024.0 if rss0 and rss1 else None
    print("    %d whispers (~%.0f MB of answers asked for) in %.1f s; map-server RSS %s -> %s KB (+%s MB); connection: %s"
          % (sent, asked_mb, time.time() - t0, rss0, rss1, "%.1f" % grew_mb if grew_mb is not None else "?",
             closed or "still open"), flush=True)
    check("the map-server closes a connection that does not read", closed is not None, closed or "still open")
    check("the map-server's memory stays bounded (+< 10 MB)", grew_mb is not None and grew_mb < 10,
          "+%.1f MB" % grew_mb if grew_mb is not None else "?")
    try:
        sock.close()
    except OSError:
        pass
    print("ALL PASSED" if all(results) else "FAILED (%d)" % results.count(False))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())

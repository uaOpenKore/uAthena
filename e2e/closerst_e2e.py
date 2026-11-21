#!/usr/bin/env python3
"""closerst_e2e.py: a kicked client must get the kick code (0x81) and a clean close (FIN), not a TCP RST.
The server closed sockets that still held unread client data, which makes the kernel answer with RST; a
Windows client then throws away what it had not read yet - the 0x81 too, so the player saw no reason.
A logs in and sends keepalives every few ms (data always in flight); a second login of A kicks it (0x81/2).
Usage: python3 -I closerst_e2e.py [rounds]"""
import errno, os, re, socket, subprocess, struct, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW  # noqa: E402

MAP_PORT = 5121
RSTLOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "closerst_tcpdump.txt")

def server_rsts(client_port):
    """RST segments the map-server sent to this client port (tcpdump runs for the whole test)."""
    n = 0
    for line in open(RSTLOG, errors="replace"):
        m = re.search(r"\.%d > [0-9.]+\.(\d+):" % MAP_PORT, line)
        if m and int(m.group(1)) == client_port and "Flags [R" in line:
            n += 1
    return n

def one_round():
    a = rostub.Session(USER, PW, log=lambda *x: None)
    a.login(); _, r = a.char_enter(); a.select_char(r[1][0][0]); assert a.map_enter()[0] == "ok"
    s = a.map_sock
    stop = threading.Event()
    def flood():
        while not stop.is_set():
            try:
                s.send(struct.pack("<HHI", 0x89, 0, int(time.time() * 1000) & 0xFFFFFFFF))
            except OSError:
                return
            time.sleep(0.002)
    t = threading.Thread(target=flood, daemon=True); t.start()
    port = s.getsockname()[1]
    time.sleep(5.0) # a kick in the first 4 s is held back as a map-transfer race
    b = rostub.Session(USER, PW, log=lambda *x: None)
    threading.Thread(target=lambda: (b.login(),), daemon=True).start()
    buf = b""; end = "timeout"; s.settimeout(1.0); deadline = time.time() + 20
    while time.time() < deadline:
        try:
            d = s.recv(65536)
        except socket.timeout:
            continue
        except OSError as e:
            end = "RST" if e.errno == errno.ECONNRESET else "error %s" % e; break
        if not d:
            end = "FIN"; break
        buf += d
    time.sleep(0.5)
    stop.set()
    time.sleep(1.0)
    rst = server_rsts(port)
    i = buf.rfind(b"\x81\x00")
    kick = buf[i + 2] if i >= 0 and i + 2 < len(buf) else None
    s.close()
    time.sleep(12) # let the second login and the save settle before the next round
    return end, kick, rst

rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
dump = subprocess.Popen(["tcpdump", "-i", "lo", "-n", "-l", "-U", "tcp src port %d and (tcp[tcpflags] & tcp-rst != 0)" % MAP_PORT],
                        stdout=open(RSTLOG, "w"), stderr=subprocess.DEVNULL)
time.sleep(1.5)
try:
    res = [one_round() for _ in range(rounds)]
finally:
    dump.terminate()
for n, (end, kick, rst) in enumerate(res):
    print("  round %d: close=%s kick=%s server_rst=%d" % (n, end, kick, rst), flush=True)
bad = [x for x in res if x[0] != "FIN" or x[1] != 2 or x[2] > 0]
if bad:
    print("FAIL  %d/%d kicks: the kicked socket was reset (RST) or the kick code was lost" % (len(bad), rounds))
    sys.exit(1)
print("ok    %d kicks closed with FIN" % rounds); print("ALL PASSED")

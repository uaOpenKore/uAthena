#!/usr/bin/env python3
"""fuzz_map.py <run dir> [rounds per packet]: a logged-in player (no GM level) sends every packet the map-server
handles (packet_ver 22, pdb22.json) with boundary and random contents: zeros, 0xFF, 0x7F/0x80 halves, each 16/32-bit
field at a time set to 0xFFFF/0x8000/0x7FFF/1, random; variable-length ones with lengths 4..2000. After each packet
type: the map-server process must be alive and answer a tick request (0x7e -> 0x7f), map.out must show no memory
manager error. A session the server closes (an invalid length etc.) is logged in again.
Prints one line per packet type that killed the server, broke memory, or stopped it answering."""
import json, os, random, socket, struct, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW  # noqa: E402

run = sys.argv[1]; rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 12
rnd = random.Random(1120)
pdb = {int(k): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdb22.json"))).items()}
SKIP = {"wanttoconnection", "quitgame", "restart", "ticksend", "debug"}
tick_cmd = [k for k, v in pdb.items() if v[1] == "ticksend"][0]
tick_len = pdb[tick_cmd][0]

def map_pid():
    for p in subprocess.run(["pgrep", "-x", "map-server_sql"], capture_output=True, text=True).stdout.split():
        if os.path.realpath("/proc/%s/cwd" % p) == os.path.realpath(run): return p
def memlog():
    t = open(os.path.join(run, "map.out"), errors="replace").read()
    return sum(t.count(k) for k in ("Memory manager: args of", "overflowed pointer", "not valid pointer", "freed pointer"))

class Conn:
    def __init__(self):
        self.s = None
    def ensure(self):
        if self.s: return
        for _ in range(5):
            try:
                p = rostub.Session(USER, PW, log=lambda *a: None)
                p.login(); _, r = p.char_enter(); p.select_char(r[1][0][0])
                if p.map_enter()[0] == "ok":
                    self.s = p.map_sock; self.s.sendall(struct.pack("<H", 0x7D)); self.drain(1.0); return
            except Exception:
                time.sleep(3)
        raise SystemExit("cannot log in")
    def drain(self, t):
        self.s.settimeout(0.05); end = time.time() + t
        while time.time() < end:
            try:
                d = self.s.recv(65536)
                if not d: self.s = None; return
            except socket.timeout: pass
            except OSError: self.s = None; return
    def send(self, b):
        try: self.s.sendall(b)
        except OSError: self.s = None
    def ping(self):
        """True when the server answers a tick request."""
        if not self.s: return None
        self.send(struct.pack("<H", tick_cmd) + bytes(tick_len - 2))
        if not self.s: return None
        self.s.settimeout(3); buf = b""; end = time.time() + 3
        while time.time() < end:
            try:
                d = self.s.recv(65536)
                if not d: self.s = None; return None
                buf += d
                if b"\x7f\x00" in buf: return True
            except socket.timeout: break
            except OSError: self.s = None; return None
        return False

def payloads(cmd, ln):
    out = []
    if ln == -1:
        for L in (4, 5, 6, 8, 16, 64, 300, 2000):
            for fill in (b"\x00", b"\xff", None):
                body = (fill * (L - 4)) if fill else bytes(rnd.getrandbits(8) for _ in range(L - 4))
                out.append(struct.pack("<HH", cmd, L) + body)
        return out
    n = ln - 2
    out += [struct.pack("<H", cmd) + bytes(n), struct.pack("<H", cmd) + b"\xff" * n, struct.pack("<H", cmd) + b"\x7f" * n,
            struct.pack("<H", cmd) + b"\x80" * n]
    for off in range(0, n - 1, 2):
        for v in (0xFFFF, 0x8000, 0x7FFF, 0x0001):
            b = bytearray(rnd.getrandbits(8) for _ in range(n)); struct.pack_into("<H", b, off, v)
            out.append(struct.pack("<H", cmd) + bytes(b))
    for off in range(0, n - 3, 2):
        for v in (0xFFFFFFFF, 0x80000000, 0x7FFFFFFF):
            b = bytearray(n); struct.pack_into("<I", b, off, v); out.append(struct.pack("<H", cmd) + bytes(b))
    for _ in range(rounds):
        out.append(struct.pack("<H", cmd) + bytes(rnd.getrandbits(8) for _ in range(n)))
    return out

c = Conn(); c.ensure()
pid0 = map_pid(); m0 = memlog(); bad = []
ONLY = [int(x, 16) for x in os.environ.get("ONLY", "").split(",") if x]
for cmd in sorted(pdb):
    if ONLY and cmd not in ONLY: continue
    ln, func, _ = pdb[cmd]
    if func in SKIP: continue
    kicked = 0
    for pkt in payloads(cmd, ln):
        c.ensure()
        c.send(pkt); c.drain(0.02)
        if not c.s: kicked += 1
    time.sleep(0.3)
    pid = map_pid(); alive = pid is not None and pid == pid0
    c.ensure() if alive else None
    pong = c.ping() if alive else None
    m = memlog()
    note = []
    if not alive: note.append("MAP-SERVER DIED")
    if alive and pong is not True: note.append("no tick answer")
    if m != m0: note.append("memory manager errors +%d" % (m - m0)); m0 = m
    status = "  ".join(note)
    print("0x%04x %-28s len %4d  kicked %3d  %s" % (cmd, func, ln, kicked, status or "ok"), flush=True)
    if note: bad.append((cmd, func, status))
    if not alive: break
print("BAD %d: %s" % (len(bad), bad))

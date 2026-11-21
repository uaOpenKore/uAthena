#!/usr/bin/env python3
"""ТЗ «разрывы связи» — «Как проверить», run against a local login+char+map stack.

usage: scenarios.py <run-dir> <s1|s2|s3|setup>
"""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402

RUN = sys.argv[1]
ACCS = {"A": ("e2etesta", "e2epass1", "E2eTesterA"), "V": ("e2etestv", "e2epass1", "E2eTesterV")}
T0 = time.time()


def log(*a):
    print("[%6.2f]" % (time.time() - T0), *a, flush=True)


def maplog_mark():
    try:
        return os.path.getsize(os.path.join(RUN, "map.out"))
    except OSError:
        return 0


def maplog_since(mark, name="map.out"):
    with open(os.path.join(RUN, name), "rb") as f:
        f.seek(mark if name == "map.out" else 0)
        txt = f.read().decode("latin-1")
    return re.sub(r"\x1b\[[0-9;]*[mK]", "", txt)


def account(key):
    user, pw, charname = ACCS[key]
    s = rostub.Session(user, pw, log=log)
    try:
        s.login()
    except RuntimeError as e:  # first run: create it through new_account (_M suffix)
        log(key, "login failed (%s) -> creating account %s_M" % (e, user))
        s = rostub.Session(user + "_M", pw, log=log)
        s.login()
        s = rostub.Session(user, pw, log=log)
        s.login()
    return s


def enter_char_select(s):
    took, res = s.char_enter()
    return took, res


def full_login(key, to_map=True):
    """login -> char select -> pick (or make) a char -> map. Returns (session, map_result)."""
    s = account(key)
    took, res = enter_char_select(s)
    if res[0] != "list":
        log(key, "char server refused:", res, "after %.1fs" % took)
        return s, ("charsel_refused", res)
    chars = res[1]
    if not chars:
        cid = s.make_char(ACCS[key][2], slot=0)
        log(key, "made char", cid)
        slot = 0
    else:
        slot = chars[0][0]
    s.select_char(slot)
    log(key, "aid=%d cid=%d lid1=%#x selected (char list after %.1fs)" % (s.aid, s.cid, s.lid1, took))
    if not to_map:
        return s, None
    r = s.map_enter()
    log(key, "map enter ->", r)
    return s, r


def s1():
    """Причины 1 и 2: dead waiting node for A, V inherits its fd, then A logs in."""
    a_probe = account("A")  # only to learn A's account id
    mark = maplog_mark()
    log("ghost: map login for A (aid=%d) with a wrong login id, connection dropped at once" % a_probe.aid)
    a_probe.map_ghost(a_probe.aid)
    time.sleep(1.0)
    v, rv = full_login("V")
    if rv[0] != "ok":
        log("V could not enter:", rv)
        return
    time.sleep(2)
    a, ra = full_login("A")
    alive, kick = v.map_alive(12)
    log("RESULT: V still connected=%s kick=%s | A map enter=%s" % (alive, kick, ra))
    out = maplog_since(mark)
    for pat in ("already authentified", "authfail_ignored", "DCMETRIC", "DROP", "not authenticated", "logged in"):
        for line in out.splitlines():
            if pat in line:
                log("  map.log:", line.strip())
    if a.map_sock:
        a.quit_game(1)
    if alive:
        v.quit_game(1)


def s2():
    """Причина 3: A enters the map, its client is killed within 10 s, A logs in again at once."""
    mark = maplog_mark()
    try:
        cmark = os.path.getsize(os.path.join(RUN, "char.out"))
    except OSError:
        cmark = 0
    a, ra = full_login("A")
    if ra[0] != "ok":
        log("A could not enter:", ra)
        return
    time.sleep(2)
    log("killing A's client (no quit packet) 2 s after map entry -> prevent_logout keeps the char 10 s")
    a.kill_map()
    t = time.time()
    a2 = account("A")
    took, res = a2.char_enter(timeout=30)
    log("RESULT: relogin char-select answer after %.1fs: %s" % (took, res[0] if res[0] == "list" else res))
    if res[0] == "list":
        a2.select_char(res[1][0][0])
        r = a2.map_enter()
        log("RESULT: relogin map enter -> %s (%.1fs after the kill)" % (r, time.time() - t))
        if r[0] == "ok":
            a2.quit_game(1)
    with open(os.path.join(RUN, "char.out"), "rb") as f:
        f.seek(cmark)
        ctxt = re.sub(r"\x1b\[[0-9;]*[mK]", "", f.read().decode("latin-1"))
    for line in ctxt.splitlines():
        if "DCMETRIC" in line or "0x81" in line:
            log("  char.log:", line.strip())
    for line in maplog_since(mark).splitlines():
        if "DCMETRIC" in line or "DROP" in line:
            log("  map.log:", line.strip())


def s3():
    """Причина 4: char select / quit are not DROPs; a killed client is peer_close."""
    mark = maplog_mark()
    a, ra = full_login("A")
    v, rv = full_login("V")
    time.sleep(12)  # past prevent_logout so the exits are allowed
    log("A -> back to character select (0xb2/1)")
    a.charselect_return(3)
    log("V -> client killed")
    v.kill_map()
    time.sleep(1)
    a3, r3 = full_login("A")
    time.sleep(12)
    log("A -> quit game (0x18a)")
    a3.quit_game(3)
    time.sleep(6)
    out = maplog_since(mark)
    for line in out.splitlines():
        if "DROP" in line or "logged off" in line or "DCMETRIC" in line:
            log("  map.log:", line.strip())


def s4():
    """Причина 4: @kick from a GM must be DROP gm_kick, not unknown."""
    import struct
    mark = maplog_mark()
    a, ra = full_login("A")
    v, rv = full_login("V")
    time.sleep(2)
    msg = ("E2eTesterA : @kick E2eTesterV").encode("latin-1")
    a.map_sock.sendall(struct.pack("<HH", 0xf3, 4 + len(msg) + 1) + msg + b"\0")
    log("A (GM) -> @kick E2eTesterV")
    alive, kick = v.map_alive(8)
    log("RESULT: V still connected=%s" % alive)
    time.sleep(1)
    for line in maplog_since(mark).splitlines():
        if "DROP" in line or "logged off" in line or "kick" in line.lower():
            log("  map.log:", line.strip())
    time.sleep(10)
    a.quit_game(2)


def s5():
    """Char selected but the client never reached the map (crashed while loading), then relogin."""
    try:
        cmark = os.path.getsize(os.path.join(RUN, "char.out"))
    except OSError:
        cmark = 0
    mark = maplog_mark()
    a, _ = full_login("A", to_map=False)
    log("A selected a char but never connects to the map; relogin 1 s later")
    time.sleep(1)
    a2 = account("A")
    took, res = a2.char_enter(timeout=40)
    log("RESULT: relogin char-select answer after %.1fs: %s" % (took, res[0] if res[0] == "list" else res))
    if res[0] == "list":
        a2.select_char(res[1][0][0])
        r = a2.map_enter()
        log("RESULT: map enter -> %s" % (r,))
        if r[0] == "ok":
            time.sleep(11)
            a2.quit_game(2)
    with open(os.path.join(RUN, "char.out"), "rb") as f:
        f.seek(cmark)
        ctxt = re.sub(r"\x1b\[[0-9;]*[mK]", "", f.read().decode("latin-1"))
    for line in ctxt.splitlines():
        if "DCMETRIC" in line:
            log("  char.log:", line.strip())
    for line in maplog_since(mark).splitlines():
        if "DCMETRIC" in line or "DROP" in line or "not authed" in line:
            log("  map.log:", line.strip())


def s6():
    """Storage capacity: account A has 400 items (> old 300 cap). @storage must report 400/600 and keep all."""
    import socket as _s
    import struct
    a, ra = full_login("A")
    if ra[0] != "ok":
        log("A could not enter:", ra)
        return
    time.sleep(2)
    msg = ("E2eTesterA : @storage").encode("latin-1")
    a.map_sock.sendall(struct.pack("<HH", 0xf3, 4 + len(msg) + 1) + msg + b"\0")
    log("A (GM) -> @storage")
    buf = b""
    end = time.time() + 6
    while time.time() < end:
        a.map_sock.settimeout(0.5)
        try:
            d = a.map_sock.recv(65536)
        except _s.timeout:
            continue
        if not d:
            break
        buf += d
    i = buf.find(b"\xf2\x00")
    found = None
    while i >= 0:
        cur, mx = struct.unpack_from("<HH", buf, i + 2)
        if mx in (300, 600, 1000):
            found = (cur, mx)
            break
        i = buf.find(b"\xf2\x00", i + 1)
    log("RESULT: storage count packet 0xF2 -> cur/max = %s (received %d bytes)" % (found, len(buf)))
    if os.environ.get("S6_TAKE"):
        # movefromkafra (ver 22: 0x00f7, 22 B, index@14 W, amount@18 L): take storage slot 1 -> storage is dirty
        pkt = struct.pack("<H", 0x00f7) + b"\0" * 12 + struct.pack("<H", 1) + b"\0\0" + struct.pack("<I", 1)
        a.map_sock.sendall(pkt)
        log("A -> take 1 item from storage slot 1 (0x00f7) -> storage becomes dirty")
        time.sleep(1)
    a.map_sock.sendall(struct.pack("<H", 0x0193))  # closekafra -> the map saves storage to the char-server
    log("A -> close storage (0x0193)")
    time.sleep(3)
    time.sleep(10)
    a.quit_game(2)


def s8():
    """Storage list chunking: open storage (400 items) and count items over ALL 0x1f0/0xa6 packets."""
    import socket as _s
    import struct
    a, ra = full_login("A")
    if ra[0] != "ok":
        log("A could not enter:", ra)
        return
    time.sleep(2)
    msg = ("E2eTesterA : @storage").encode("latin-1")
    a.map_sock.sendall(struct.pack("<HH", 0xf3, 4 + len(msg) + 1) + msg + b"\0")
    buf = b""
    end = time.time() + 6
    while time.time() < end:
        a.map_sock.settimeout(0.5)
        try:
            d = a.map_sock.recv(65536)
        except _s.timeout:
            continue
        if not d:
            break
        buf += d
    total = 0
    pkts = []
    seen_idx = set()
    dup = 0
    for cmd, size in ((0x1f0, 18), (0xa6, 20)):
        i = buf.find(struct.pack("<H", cmd))
        while i >= 0:
            if i + 4 <= len(buf):
                ln = struct.unpack_from("<H", buf, i + 2)[0]
                if ln >= 4 + size and (ln - 4) % size == 0 and i + ln <= len(buf):
                    n = (ln - 4) // size
                    for k in range(n):
                        idx = struct.unpack_from("<H", buf, i + 4 + k * size)[0]
                        if idx in seen_idx:
                            dup += 1
                        seen_idx.add(idx)
                    total += n
                    pkts.append((hex(cmd), ln, n))
                    i = buf.find(struct.pack("<H", cmd), i + ln)
                    continue
            i = buf.find(struct.pack("<H", cmd), i + 1)
    log("RESULT: storage list packets %s -> %d items, %d distinct indexes, %d duplicates, max packet %d bytes"
        % (pkts, total, len(seen_idx), dup, max([p[1] for p in pkts] or [0])))
    a.map_sock.sendall(struct.pack("<H", 0x0193))
    time.sleep(12)
    a.quit_game(2)


def s7():
    """Inventory > 100: char A has 250 items in the DB. Count the items in the inventory list packets."""
    import socket as _s
    import struct
    a, ra = full_login("A")
    if ra[0] != "ok":
        log("A could not enter:", ra)
        return
    buf = b""
    end = time.time() + 5
    while time.time() < end:
        a.map_sock.settimeout(0.5)
        try:
            d = a.map_sock.recv(65536)
        except _s.timeout:
            continue
        if not d:
            break
        buf += d
    stack = equip = 0
    for cmd, size in ((0x1ee, 18), (0xa4, 20)):
        i = buf.find(struct.pack("<H", cmd))
        while i >= 0:
            ln = struct.unpack_from("<H", buf, i + 2)[0]
            if ln >= 4 and (ln - 4) % size == 0 and i + ln <= len(buf):
                n = (ln - 4) // size
                if cmd == 0x1ee:
                    stack += n
                else:
                    equip += n
                log("  packet 0x%04x len=%d -> %d items" % (cmd, ln, n))
                break
            i = buf.find(struct.pack("<H", cmd), i + 1)
    log("RESULT: inventory items received = %d (stackable %d + equip %d)" % (stack + equip, stack, equip))
    time.sleep(10)
    a.quit_game(2)


if __name__ == "__main__":
    {"s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6, "s7": s7, "s8": s8, "setup": lambda: (full_login("A")[0].quit_game(1), full_login("V")[0].quit_game(1))}[sys.argv[2]]()

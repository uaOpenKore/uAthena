#!/usr/bin/env python3
"""Shared helpers for the c1 TXT e2e tests (packet framer copied from e2e/tools/elemark_e2e.py)."""
import os
import re
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402  (c1 copy: ports 16900/16121/15121)

PACKET_TABLE = "/root/BornRok/src/net/PacketTable.cpp"   # read-only


def load_lengths(path=PACKET_TABLE):
    txt = open(path, encoding="utf-8").read()
    return {int(a, 16): int(b) for a, b in re.findall(r"\{0x([0-9a-fA-F]{4}),(-?\d+)\}", txt)}


class Stream:
    def __init__(self, sock, lengths):
        self.s, self.L, self.buf = sock, lengths, b""
        self.next_keepalive = 0.0

    def packets(self, seconds):
        """Yield (id, bytes) for every packet that arrives within `seconds`."""
        end = time.time() + seconds
        while True:
            while len(self.buf) >= 2:
                pid = struct.unpack_from("<H", self.buf)[0]
                ln = self.L.get(pid, 0)
                if ln == 0:
                    raise RuntimeError("unknown packet 0x%04x: stream framing lost" % pid)
                if ln < 0:
                    if len(self.buf) < 4:
                        break
                    ln = struct.unpack_from("<H", self.buf, 2)[0]
                if len(self.buf) < ln:
                    break
                pkt, self.buf = self.buf[:ln], self.buf[ln:]
                yield pid, pkt
            left = end - time.time()
            if left <= 0:
                return
            if time.time() >= self.next_keepalive:
                self.s.sendall(struct.pack("<HHI", 0x89, 0, int(time.time() * 1000) & 0xFFFFFFFF))
                self.next_keepalive = time.time() + 5
            self.s.settimeout(min(left, 0.5))
            try:
                d = self.s.recv(65536)
            except socket.timeout:
                continue
            if not d:
                raise ConnectionError("map server closed the connection")
            self.buf += d

    def collect(self, seconds):
        """All packets of the next `seconds` as a list of (id, bytes)."""
        return list(self.packets(seconds))


def messages(pkts):
    """Texts of the 0x8e (atcommand output) and 0x17f (dispbottom) packets in `pkts`.
    clif_disp_onlyself sends len+5 bytes but copies only len: the last byte of a 0x17f is garbage."""
    out = []
    for pid, p in pkts:
        if pid == 0x8E:
            out.append(p[4:].split(b"\0")[0].decode("latin-1"))
        elif pid == 0x17F:
            out.append(p[4:-1].split(b"\0")[0].decode("latin-1"))
    return out


def chat(sock, name, text):
    msg = ("%s : %s" % (name, text)).encode("latin-1") + b"\0"
    sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)


def whisper(sock, target, text):
    """0x0096 <len>.W <target>.24B <message>.?B"""
    msg = text.encode("latin-1") + b"\0"
    sock.sendall(struct.pack("<HH", 0x96, 28 + len(msg)) + rostub._fixed(target, 24) + msg)


def strip_ansi(s):
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def read_out(run, name):
    try:
        return strip_ansi(open(os.path.join(run, name + ".out"), encoding="utf-8", errors="replace").read())
    except FileNotFoundError:
        return ""


def ensure_account(user, pw):
    """TXT auto-registration: log in once as <user>_M (new_account: yes), then plain <user>."""
    s = rostub.Session(user, pw)
    try:
        s.login()
        return "existing"
    except RuntimeError:
        pass
    reg = rostub.Session(user + "_M", pw)
    reg.login()
    time.sleep(0.5)
    rostub.Session(user, pw).login()
    return "created"


def enter_map(user, pw, name, log=print):
    """Login -> char select (creates `name` in slot 0 when the account has no char) -> map enter + LoadEndAck.
    Returns the rostub.Session (map_sock connected)."""
    end = time.time() + 30
    while True:   # the login-server refuses an account it still holds online (code 3) right after a logout
        s = rostub.Session(user, pw)
        try:
            s.login()
            break
        except RuntimeError as e:
            if time.time() >= end or "code=3" not in str(e):
                raise
            time.sleep(2)
    _, res = s.char_enter()
    if res[0] != "list":
        raise RuntimeError("char server refused: %r" % (res,))
    chars = res[1]
    if not chars:
        cid = s.make_char(name, slot=0)
        log("  created char %s cid=%d" % (name, cid))
        slot = 0
    else:
        slot = chars[0][0]
    s.select_char(slot)
    res = s.map_enter()
    if res[0] != "ok":
        raise RuntimeError("map enter failed: %r" % (res,))
    return s

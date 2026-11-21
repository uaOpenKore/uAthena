#!/usr/bin/env python3
"""Minimal uaRO (serverType 8) client stub for e2e tests of the login/char/map auth flow.

Only what the ТЗ «разрывы связи» scenarios need: login (0x64), char-server enter (0x65),
make/select char (0x67/0x66), map enter (0x9b, 26 B), LoadEndAck (0x7d), keepalive (0x89),
return to char select (0xb2/1), quit (0x18a).
"""
import socket
import struct
import time

HOST = "127.0.0.1"
LOGIN_PORT, CHAR_PORT, MAP_PORT = 6900, 6121, 5121


def _recv_exact(s, n, deadline):
    buf = b""
    while len(buf) < n:
        left = deadline - time.time()
        if left <= 0:
            raise TimeoutError("timeout waiting for %d bytes (got %d)" % (n, len(buf)))
        s.settimeout(left)
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("connection closed by server (got %d/%d bytes)" % (len(buf), n))
        buf += chunk
    return buf


def _fixed(text, size):
    b = text.encode("latin-1")[: size - 1]
    return b + b"\0" * (size - len(b))


class Session:
    def __init__(self, user, password, log=print):
        self.user, self.password, self.log = user, password, log
        self.aid = self.lid1 = self.lid2 = self.sex = None
        self.cid = None
        self.map_sock = None
        self.char_sock = None

    # ---------------------------------------------------------------- login
    def login(self, timeout=10):
        s = socket.create_connection((HOST, LOGIN_PORT), timeout=timeout)
        try:
            s.sendall(struct.pack("<HI", 0x64, 20) + _fixed(self.user, 24) + _fixed(self.password, 24) + b"\0")
            dl = time.time() + timeout
            cmd = struct.unpack("<H", _recv_exact(s, 2, dl))[0]
            if cmd == 0x69:
                ln = struct.unpack("<H", _recv_exact(s, 2, dl))[0]
                body = _recv_exact(s, ln - 4, dl)
                self.lid1, self.aid, self.lid2 = struct.unpack_from("<III", body, 0)
                self.sex = body[42]
                return True
            if cmd == 0x6a:
                rest = _recv_exact(s, 21, dl)
                raise RuntimeError("login refused 0x6a code=%d" % rest[0])
            if cmd == 0x81:
                rest = _recv_exact(s, 1, dl)
                raise RuntimeError("login refused 0x81 code=%d" % rest[0])
            raise RuntimeError("login: unexpected packet 0x%04x" % cmd)
        finally:
            s.close()

    # ----------------------------------------------------------- char server
    def char_enter(self, timeout=30):
        """Connect to the char server; returns (elapsed_s, ('list', chars) | ('refused', cmd, code))."""
        s = socket.create_connection((HOST, CHAR_PORT), timeout=timeout)
        self.char_sock = s
        t0 = time.time()
        s.sendall(struct.pack("<HIIIHB", 0x65, self.aid, self.lid1, self.lid2, 0, self.sex))
        dl = t0 + timeout
        _recv_exact(s, 4, dl)  # account id echo
        cmd = struct.unpack("<H", _recv_exact(s, 2, dl))[0]
        if cmd == 0x6b:
            ln = struct.unpack("<H", _recv_exact(s, 2, dl))[0]
            body = _recv_exact(s, ln - 4, dl)[20:]
            chars = []
            if body:
                size = 108 if len(body) % 108 == 0 else 106
                for off in range(0, len(body), size):
                    cid = struct.unpack_from("<I", body, off)[0]
                    slot = struct.unpack_from("<H", body, off + 104)[0]
                    chars.append((slot, cid))
            return time.time() - t0, ("list", chars)
        if cmd in (0x6c, 0x81):
            code = _recv_exact(s, 1, dl)[0]
            return time.time() - t0, ("refused", cmd, code)
        raise RuntimeError("char_enter: unexpected packet 0x%04x" % cmd)

    def make_char(self, name, slot=0, timeout=10):
        s = self.char_sock
        s.sendall(struct.pack("<H", 0x67) + _fixed(name, 24) + bytes([5, 5, 5, 5, 5, 5, slot]) + struct.pack("<HH", 1, 1))
        dl = time.time() + timeout
        cmd = struct.unpack("<H", _recv_exact(s, 2, dl))[0]
        if cmd == 0x6d:
            entry = _recv_exact(s, 106, dl)
            # 108-byte entries (char_rename on) carry 2 more bytes: swallow them if they come
            try:
                _recv_exact(s, 2, time.time() + 0.5)
            except TimeoutError:
                pass
            return struct.unpack_from("<I", entry, 0)[0]
        if cmd == 0x6e:
            raise RuntimeError("make_char refused code=%d" % _recv_exact(s, 1, dl)[0])
        raise RuntimeError("make_char: unexpected packet 0x%04x" % cmd)

    def select_char(self, slot, timeout=15):
        s = self.char_sock
        s.sendall(struct.pack("<HB", 0x66, slot))
        dl = time.time() + timeout
        while True:
            cmd = struct.unpack("<H", _recv_exact(s, 2, dl))[0]
            if cmd == 0x71:
                body = _recv_exact(s, 26, dl)
                self.cid = struct.unpack_from("<I", body, 0)[0]
                s.close()
                self.char_sock = None
                return self.cid
            if cmd in (0x6c, 0x81):
                raise RuntimeError("select refused 0x%04x code=%d" % (cmd, _recv_exact(s, 1, dl)[0]))
            raise RuntimeError("select: unexpected packet 0x%04x" % cmd)

    # ------------------------------------------------------------ map server
    def map_enter(self, cid=None, lid1=None, timeout=15, pad13=b"\x37\x33\x36\x64"):
        """Send the map login. Returns ('ok', None) | ('refused', code) | ('timeout', None)."""
        s = socket.create_connection((HOST, MAP_PORT), timeout=timeout)
        self.map_sock = s
        pkt = (struct.pack("<H", 0x9b) + b"\x39\x33" + struct.pack("<I", self.aid) + b"\x65"
               + struct.pack("<I", cid if cid is not None else self.cid) + pad13
               + struct.pack("<I", lid1 if lid1 is not None else self.lid1)
               + struct.pack("<I", int(time.time() * 1000) & 0xFFFFFFFF) + bytes([self.sex or 0]))
        assert len(pkt) == 26
        s.sendall(pkt)
        dl = time.time() + timeout
        try:
            _recv_exact(s, 4, dl)  # account id echo
            cmd = struct.unpack("<H", _recv_exact(s, 2, dl))[0]
        except TimeoutError:
            return ("timeout", None)
        if cmd == 0x73:
            _recv_exact(s, 9, dl)
            s.sendall(struct.pack("<H", 0x7d))  # LoadEndAck
            return ("ok", None)
        if cmd == 0x81:
            return ("refused", _recv_exact(s, 1, dl)[0])
        return ("unexpected", cmd)

    def map_ghost(self, aid, cid=1, lid1=0x1234567):
        """Connect, send a map login for `aid` and drop the connection at once (ТЗ Причина 1, step 1)."""
        s = socket.create_connection((HOST, MAP_PORT), timeout=5)
        pkt = (struct.pack("<H", 0x9b) + b"\x39\x33" + struct.pack("<I", aid) + b"\x65"
               + struct.pack("<I", cid) + b"\x37\x33\x36\x64" + struct.pack("<I", lid1)
               + struct.pack("<I", 0) + b"\x00")
        s.sendall(pkt)
        try:
            _recv_exact(s, 4, time.time() + 3)  # wait for the aid echo: the node now exists
        except Exception:
            pass
        s.close()

    def map_alive(self, seconds):
        """Keep the map session alive (keepalive every 5 s) and drain input for `seconds`.
        Returns (alive, kick_code_or_None). A 0x81 is spotted by a raw scan of the stream."""
        s = self.map_sock
        end = time.time() + seconds
        next_tick = 0
        kick = None
        while time.time() < end:
            if time.time() >= next_tick:
                try:
                    s.sendall(struct.pack("<HHI", 0x89, 0, int(time.time() * 1000) & 0xFFFFFFFF))
                except OSError:
                    return False, kick
                next_tick = time.time() + 5
            s.settimeout(0.5)
            try:
                data = s.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                return False, kick
            if not data:
                return False, kick
            i = data.find(b"\x81\x00")
            if i >= 0 and i + 2 < len(data) and kick is None and len(data) - i <= 8:
                kick = data[i + 2]
        return True, kick

    def kill_map(self):
        """Drop the map connection without a quit packet (= the client process was killed)."""
        if self.map_sock:
            self.map_sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            self.map_sock.close()
            self.map_sock = None

    def charselect_return(self, wait=3):
        """0xb2/1 = back to character select; the server answers 0xb3 and we close."""
        self.map_sock.sendall(struct.pack("<HB", 0xb2, 1))
        time.sleep(wait)
        self.map_sock.close()
        self.map_sock = None

    def quit_game(self, wait=2):
        self.map_sock.sendall(struct.pack("<HH", 0x18a, 0))
        time.sleep(wait)
        self.map_sock.close()
        self.map_sock = None

#!/usr/bin/env python3
"""s2sauth_e2e.py <host-not-loopback>: the server-to-server logins must not be open to the network.
From a non-loopback address (this host's own LAN address: the connection comes FROM it, as a remote one would):
  1 char-server 6121: 0x2af8 "log in as a map-server" with the right userid/passwd must be refused (0x2af9 != 0)
  2 char-server 6121: a wrong password must end the connection, not allow the next guess on it
  3 login-server 6900: 0x2710 "log in as a char-server" must be refused
From 127.0.0.1 the real servers keep working (the stand's map/char are connected at all)."""
import os, socket, struct, sys, time

host = sys.argv[1]
only = sys.argv[2] if len(sys.argv) > 2 else ""  # "login": the char-server is down (its slot free)
def recv_n(s, n, t=3):
    s.settimeout(t); b = b""
    try:
        while len(b) < n:
            d = s.recv(n - len(b))
            if not d: return b, "closed"
            b += d
    except socket.timeout:
        return b, "timeout"
    return b, "ok"

def mapserver_login(user, pw, s=None):
    s = s or socket.create_connection((host, int(os.environ.get("CHAR_PORT", "6121"))), timeout=3)
    s.sendall(struct.pack("<H24s24sIIH", 0x2af8, user.encode(), pw.encode(), 0, 0x7f000001, 5199))
    b, st = recv_n(s, 3)
    return s, (b[2] if len(b) == 3 and struct.unpack_from("<H", b)[0] == 0x2af9 else None), st

ok = True
if only != "login":
  s, r, st = mapserver_login("s1", "p1")
  print("1 map-server login from %s with the right password: result %s (%s)" % (host, r, st))
  if r == 0:
      print("FAIL  a remote host became a map-server of this char-server"); ok = False
  s.close()

  s, r, st = mapserver_login("s1", "wrong1")
  r2 = st2 = None
  try:
      _, r2, st2 = mapserver_login("s1", "wrong2", s)
  except OSError as e:
      st2 = "closed (%s)" % e.__class__.__name__
  print("2 wrong password: result %s; a second guess on the same connection: %s %s" % (r, r2, st2))
  if r2 is not None:
      print("FAIL  the connection stays open for the next password guess"); ok = False
  s.close()

c = socket.create_connection((host, int(os.environ.get("LOGIN_PORT", "6900"))), timeout=3)
c.sendall(struct.pack("<H24s24sIIH20sHHH", 0x2710, b"s1", b"p1", 0, 0x7f000001, 6199, b"fake", 0, 0, 0))
b, st = recv_n(c, 3)
r = b[2] if len(b) == 3 and struct.unpack_from("<H", b)[0] == 0x2711 else None
print("3 char-server login to the login-server from %s: result %s (%s)" % (host, r, st))
if r == 0:
    print("FAIL  a remote host became a char-server of this login-server"); ok = False
c.close()
if not ok:
    sys.exit(1)
print("ok    server-to-server logins refused from %s" % host); print("ALL PASSED")

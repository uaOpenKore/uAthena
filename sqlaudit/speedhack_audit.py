#!/usr/bin/env python3
"""speedhack_audit.py <run dir>: what the map-server accepts from a client that sends faster than allowed (S. 2026-11-21).
An audit, not a pass/fail of a feature: each check sends far more than the character may do and counts what the
server carried out, against what its own numbers allow. A check FAILs when the server did more than allowed.
 A attacks: 0x190 (attack once) 20 times a second for 10 s at a Pupa: hits (0x8a from us) vs 10 s / attack delay
 B Bash spam: 0x72 skill 5 20 times a second for 10 s: Bash hits (0x1de) vs 10 s / attack delay
 C potions: 0x9f Red Potion 20 times a second for 10 s: potions used (0xa8 ok) vs the item-use delay (reported)
 D walking: a walk request 10 times a second for 6 s: cells moved (server positions) vs 6 s / walk speed
 E a far walk: one request 60 cells away: does the server walk it (path limit)
 F walking while attacking: alternating walk/attack requests 20 times a second (both counted)
The character: Swordsman lv 80 on prontera (GM 99 for @monster), STR 1 so the Pupa lives long."""
import os, struct, subprocess, sys, time
# On the e2e stand (ports 6900.., the local `ragnarok` DB, the worktree's conf/db/npc): the SQL audit stand runs
# the 19.11 data, where a character's attacks on monsters do nothing.
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/e2e/tools")
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-N", "-B", "-e"]
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
L = load_lengths("/root/BornRok/src/net/PacketTable.cpp")
def chat(sock, name, text):
    msg = ("%s : %s" % (name, text)).encode("latin-1") + b"\0"
    sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)
A = C = 900200000
def enter_map(user, pw, name, log=None):
    s = rostub.Session(user, pw, log=lambda *a: None); s.login(); s.char_enter(); s.select_char(0)
    if s.map_enter()[0] != "ok":
        raise RuntimeError("map enter failed")
    return s
PUPA, REDPOT = 1008, 501
ok = True
rows = []
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d else ""), flush=True); ok = ok and c
def stop(): subprocess.run(["bash", SCR + "/e2e/tools/srv.sh", "stop", run], stdout=subprocess.DEVNULL)
def start(): subprocess.run(["bash", SCR + "/e2e/tools/srv.sh", "start", run], stdout=subprocess.DEVNULL); time.sleep(4)

def walk_pkt(x, y):  # 0xa7 (v22): 3 pad bytes, then x,y packed in 3 bytes
    return struct.pack("<H", 0xa7) + b"\0" * 3 + bytes([x >> 2, ((x & 3) << 6) | (y >> 4), (y & 15) << 4])
def attack_pkt(target):  # 0x190 actionrequest (v22): target at 5, action at 18 (0 = attack once)
    return struct.pack("<H", 0x190) + b"\0" * 3 + struct.pack("<I", target) + b"\0" * 9 + bytes([0])
def skill_pkt(skill, lv, target):  # 0x72 useskilltoid (v22): lv at 6, skill at 10, target at 21
    return struct.pack("<H", 0x72) + b"\0" * 4 + struct.pack("<H", lv) + b"\0" * 2 + struct.pack("<H", skill) + b"\0" * 9 + struct.pack("<I", target)
def useitem_pkt(index, aid):  # 0x9f useitem (v22): index at 4, account id at 10
    return struct.pack("<H", 0x9f) + b"\0" * 2 + struct.pack("<H", index) + b"\0" * 4 + struct.pack("<I", aid)

class P:
    def __init__(self):
        self.s = enter_map("spdaudit", "spdpw1", "SpdAudit", log=lambda *a: None)
        self.sock = self.s.map_sock; self.st = Stream(self.sock, L)
        self.aid = self.s.account_id if hasattr(self.s, "account_id") else int(sql("SELECT account_id FROM login WHERE userid='spdaudit'"))
        self.gid = None; self.amotion = None; self.speed = None; self.pos = None; self.pots = None
        self.mob = None; self.mob_dead = False
    def handle(self, pid, p, counts):
        if pid == 0x8a:  # damage: src@2 dst@6 ... type@26
            src, dst = struct.unpack_from("<II", p, 2)
            if src == self.gid and p[26] in (0, 8, 10): counts["hit"] = counts.get("hit", 0) + 1
        elif pid == 0x1de:
            sid, src = struct.unpack_from("<HI", p, 2)
            if src == self.gid and sid == 5: counts["bash"] = counts.get("bash", 0) + 1
        elif pid == 0xa8:  # useitemack index@2 amount@4 ok@6
            if p[6]: counts["pot"] = counts.get("pot", 0) + 1
        elif pid == 0x1c8:  # useitemack2 index@2 nameid@4 id@6 amount@10 ok@12
            if p[12]: counts["pot"] = counts.get("pot", 0) + 1
        elif pid == 0xb0:
            typ, val = struct.unpack_from("<Hi", p, 2)
            if typ == 53: self.amotion = val   # SP_ASPD
            elif typ == 0: self.speed = val    # SP_SPEED
        elif pid == 0x87:  # walkok: tick@2 packed src/dst@6
            b = p[6:12]
            self.pos = ((b[0] << 2) | (b[1] >> 6), ((b[1] & 0x3f) << 4) | (b[2] >> 4))
            counts.setdefault("walks", []).append((time.time(), self.pos, ((b[2] & 0x0f) << 6) | (b[3] >> 2), ((b[3] & 0x03) << 8) | b[4]))
        elif pid == 0x88:  # fixpos id@2 x@6 y@8
            if struct.unpack_from("<I", p, 2)[0] == self.gid:
                counts.setdefault("fix", []).append(struct.unpack_from("<HH", p, 6))
        elif pid in (0x78, 0x7c, 0x22a, 0x22b) and len(p) >= 22:
            if struct.unpack_from("<H", p, 20 if pid == 0x7c else 14)[0] == PUPA:
                self.mob = struct.unpack_from("<I", p, 2)[0]; self.mob_dead = False
                if pid == 0x7c:  # packed position at 36
                    b = p[36:39]; self.mobpos = ((b[0] << 2) | (b[1] >> 6), ((b[1] & 0x3f) << 4) | (b[2] >> 4))
        elif pid == 0x80:
            if struct.unpack_from("<I", p, 2)[0] == self.mob and p[6] == 1: self.mob_dead = True
        elif pid == 0x91 or pid == 0x92:
            counts["warped"] = True
    def pump(self, sec, counts=None):
        counts = {} if counts is None else counts
        for pid, p in self.st.packets(sec): self.handle(pid, p, counts)
        return counts
    def cmd(self, t): chat(self.sock, "SpdAudit", t); self.pump(0.6)
    def spawn(self):
        """a Pupa, and the character steps next to it (the server answers 0x139 'out of range' and does not
        walk there itself)"""
        self.mob = None; self.mobpos = None
        self.cmd("@monster %d 1" % PUPA); self.pump(1.0)
        if self.mobpos:
            self.sock.sendall(walk_pkt(self.mobpos[0] + 1, self.mobpos[1])); self.pump(1.5)
        return self.mob

try:
    stop()
    sql("DELETE FROM skill WHERE char_id=%d; DELETE FROM inventory WHERE char_id=%d; DELETE FROM `char` WHERE char_id=%d; DELETE FROM login WHERE account_id=%d" % (C, C, C, A))
    sql("INSERT INTO login (account_id,userid,user_pass,sex,email,level) VALUES (%d,'spdaudit','spdpw1','M','a@a.com',99)" % A)
    sql("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,job_level,str,agi,dex,`int`,zeny,hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) "
        "VALUES (%d,%d,0,'SpdAudit',1,80,40,1,1,1,99,1000,5000,5000,800,800,'prontera',150,180,'prontera',150,180)" % (C, A))
    cid = str(C)
    sql("REPLACE INTO skill (char_id, id, lv) VALUES (%s, 5, 10)" % cid)
    sql("DELETE FROM inventory WHERE char_id=%s" % cid)
    sql("INSERT INTO inventory (char_id, nameid, amount, identify) VALUES (%s, %d, 100, 1)" % (cid, REDPOT))  # 1000 made the character overweight: no attacks, no items
    start()
    p = P(); c = p.pump(3); p.gid = int(cid) if False else None
    p.gid = int(sql("SELECT account_id FROM `char` WHERE char_id=%s" % cid))  # a player's block id is its account id
    p.cmd("@heal"); p.cmd("@allskill")
    print("ASPD amotion %s ms, walk speed %s ms/cell" % (p.amotion, p.speed), flush=True)
    amotion = p.amotion or 1000; speed = p.speed or 150
    sx0, sy0 = 150, 180

    def measure(send, every, secs, key, respawn=True):
        """send() every `every` s for `secs` s; the count of `key` the server answered with"""
        c = {}; t0 = time.time(); nxt = t0
        if respawn: p.spawn()
        while time.time() - t0 < secs:
            if respawn and (p.mob_dead or p.mob is None): p.spawn()
            if time.time() >= nxt:
                send(); nxt += every
            p.pump(0.02, c)
        p.pump(1, c)
        return c.get(key, 0) if key else c
    allowed = int(10000 / amotion) + 2
    # A attacks: at the attack delay (what a client may do) and 20 a second
    pa = measure(lambda: p.sock.sendall(attack_pkt(p.mob)), amotion / 1000.0 + 0.05, 10, "hit")
    sa = measure(lambda: p.sock.sendall(attack_pkt(p.mob)), 0.05, 10, "hit")
    check("A attacks 20/s for 10 s: %d hits (paced at the attack delay: %d), the delay allows %d" % (sa, pa, allowed), sa <= allowed and pa > 0)
    rows.append(("A attack 0x190", "paced %d / 20/s" % pa, sa, allowed))
    # B Bash
    p.cmd("@heal")
    pb = measure(lambda: p.sock.sendall(skill_pkt(5, 1, p.mob)), amotion / 1000.0 + 0.05, 10, "bash")
    p.cmd("@heal")
    sb = measure(lambda: p.sock.sendall(skill_pkt(5, 1, p.mob)), 0.05, 10, "bash")
    check("B Bash 20/s for 10 s: %d hits (paced: %d), the delay allows %d" % (sb, pb, allowed), sb <= allowed and pb > 0)
    rows.append(("B Bash 0x72", "paced %d / 20/s" % pb, sb, allowed))
    # C potions: 20 a second (pre-renewal has no item-use delay of its own)
    p.cmd("@heal")
    pots = measure(lambda: p.sock.sendall(useitem_pkt(2, p.gid)), 0.05, 10, "pot", respawn=False)
    print("    C potions 20/s for 10 s: %d used" % pots, flush=True)
    rows.append(("C Red Potion 0x9f", "20/s", pots, "-"))
    # D walking: requests 10 a second toward a cell 30 east; the server's own positions (0x87 src) over 6 s
    p.cmd("@heal")
    p.sock.sendall(walk_pkt(sx0, sy0)); p.pump(3)  # back to the start cell
    c = measure(lambda: p.sock.sendall(walk_pkt(sx0 + 12, sy0)), 0.1, 6, None, respawn=False)
    w = c.get("walks", [])
    moved = abs(w[-1][1][0] - w[0][1][0]) + abs(w[-1][1][1] - w[0][1][1]) if len(w) > 1 else 0
    secs = (w[-1][0] - w[0][0]) if len(w) > 1 else 0
    allow_w = int(secs * 1000 / speed) + 2
    check("D walk requests 10/s: moved %d cells in %.1f s, the walk speed (%d ms a cell) allows %d" % (moved, secs, speed, allow_w),
          moved <= allow_w and len(w) > 1, "walk acks=%d" % len(w))
    rows.append(("D walk 0xa7", "10/s", moved, allow_w))
    # E one request far away (the server's path search limit)
    c = measure(lambda: p.sock.sendall(walk_pkt(sx0 - 60, sy0)), 99, 3, None, respawn=False)
    w = c.get("walks", [])
    print("    E one walk request ~85 cells away: %s" % ("walked (dst %s)" % (w[-1][2:],) if w else "refused (no walk ack)"), flush=True)
    rows.append(("E far walk", 1, len(w), "path limit"))
    # F walk between attacks (cancelling the attack delay)
    p.cmd("@heal"); i = [0]
    def alt():
        p.sock.sendall(attack_pkt(p.mob) if i[0] % 2 == 0 else walk_pkt(sx0 + (i[0] % 4), sy0)); i[0] += 1
    sf = measure(alt, 0.05, 10, "hit")
    check("F walking between attacks 20/s: %d hits, the delay allows %d" % (sf, allowed), sf <= allowed)
    rows.append(("F walk+attack", "20/s", sf, allowed))
    p.s.quit_game(wait=2)
finally:
    stop()
    sql("DELETE FROM skill WHERE char_id=%d; DELETE FROM inventory WHERE char_id=%d; DELETE FROM `char` WHERE char_id=%d; DELETE FROM login WHERE account_id=%d;"
        " ALTER TABLE login AUTO_INCREMENT=1; ALTER TABLE `char` AUTO_INCREMENT=1" % (C, C, C, A))
    print("\n%-22s %8s %9s %10s" % ("check", "sent", "accepted", "allowed"))
    for r in rows: print("%-22s %8s %9s %10s" % r)
print("ALL WITHIN LIMITS" if ok else "OVER THE LIMIT SOMEWHERE")
sys.exit(0 if ok else 1)

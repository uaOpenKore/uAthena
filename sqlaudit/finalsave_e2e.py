#!/usr/bin/env python3
"""finalsave_e2e.py <run dir> [N]: every online character's final save reaches the database at a shutdown.
Prod 21.11 03:01: 281 players online at the restart, the char-server wrote 217 final saves, the rest (64) lost
what they did since their last autosave (one stood back in Alberta with job level 9). N characters (default 250)
are made in the DB at prontera 150,150, log in, each walks to 152,152 (autosave is set to an hour, so only the
final save can carry the new spot), the stand is stopped; every row must then say 152,152."""
import os, struct, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
E2E = os.environ.get("STAND") == "e2e"  # STAND=e2e: the e2e stand (ports 6900.., the local `ragnarok` DB)
sys.path.insert(0, SCR + ("/e2e/tools" if E2E else "/c1/e2e"))
import rostub  # noqa: E402
SP = SCR + "/e2e/tools" if E2E else os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 250
MY = (["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-N", "-B"] if E2E else
      ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B"])
def sql(q): return subprocess.run(MY + ["-e", q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
def sqlf(text): subprocess.run(MY, input=text, text=True, check=True)
A0 = C0 = 900000000
MAPCONF = os.path.join(run, "conf", "import", "map_conf.txt")
def cleanup():
    sqlf("DELETE FROM `char` WHERE char_id>=%d AND char_id<%d; DELETE FROM login WHERE account_id>=%d AND account_id<%d;" % (C0, C0 + 100000, A0, A0 + 100000))
def srv(a): subprocess.run(["bash", os.path.join(SP, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
def walk(sock, x, y):
    sock.sendall(struct.pack("<H", 0xA7) + bytes(3) + bytes([(x >> 2) & 0xFF, ((x << 6) | ((y >> 4) & 0x3F)) & 0xFF, (y << 4) & 0xFF]))

srv("stop"); cleanup()
conf0 = open(MAPCONF).read()
open(MAPCONF, "w").write(conf0 + "\nautosave_time: 3600\n")
try:
    rows = []
    for i in range(N):
        a, c = A0 + i, C0 + i
        rows.append("INSERT INTO login (account_id,userid,user_pass,sex,email) VALUES (%d,'fsv%d','fspw1','M','a@a.com');" % (a, i))
        rows.append("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,job_level,hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) "
                    "VALUES (%d,%d,0,'FSV%d',0,10,9,100,100,10,10,'prontera',150,150,'prontera',150,150);" % (c, a, i))
    sqlf("SET autocommit=0;\n" + "\n".join(rows) + "\nCOMMIT;\n")
    srv("start"); time.sleep(8)
    sessions = []
    for i in range(N):
        s = rostub.Session("fsv%d" % i, "fspw1", log=lambda *a: None)
        s.login(); _, r = s.char_enter(); s.select_char(0)
        if s.map_enter()[0] != "ok":
            raise RuntimeError("fsv%d did not enter the map" % i)
        walk(s.map_sock, 152, 152)
        sessions.append(s)
    time.sleep(5)  # every walk is done; nothing was saved since the login (autosave 1 h)
    moved_before = sql("SELECT COUNT(*) FROM `char` WHERE char_id>=%d AND char_id<%d AND last_x=152 AND last_y=152" % (C0, C0 + N))
    # like systemd (uAmap stops before uAchar): the map-server alone first, the char-server once it is gone
    t0 = time.time()
    if E2E:
        pid = int(open(os.path.join(run, "map.pid")).read())
        os.kill(pid, 2)
        while time.time() - t0 < 120:
            try: os.kill(pid, 0)
            except ProcessLookupError: break
            time.sleep(0.2)
    t1 = time.time()
    srv("stop")
    moved = int(sql("SELECT COUNT(*) FROM `char` WHERE char_id>=%d AND char_id<%d AND last_x=152 AND last_y=152" % (C0, C0 + N)))
    ok = moved == N
    print("%s  %d online at the shutdown, %d final saves reached the database (before the stop: %s); stop took %.1f s"
          % ("ok  " if ok else "FAIL", N, moved, moved_before, t1 - t0), flush=True)
    for s in sessions:
        try: s.map_sock.close()
        except Exception: pass
finally:
    srv("stop")
    open(MAPCONF, "w").write(conf0)
    cleanup()
sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""playlimit_txt_e2e.py <run dir>: the daily play-time limit on the TXT stand (daily_play_limit 12).
1 a first start writes save/play_reset.txt with today's date; 2 a session of ~70 s is saved to
save/playtime.txt as 1 minute of today; 3 with 720 minutes of today in playtime.txt the player is refused at
the map login (the message at once, disconnected ~40 s later); 4 a playtime.txt line of yesterday counts 0."""
import datetime, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2elib import Stream, chat, enter_map, ensure_account, load_lengths, messages  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
run = sys.argv[1]
L = load_lengths()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def srv(a): subprocess.run(["bash", os.path.join(HERE, "srv.sh"), a, run], stdout=subprocess.DEVNULL)
def save(name): return os.path.join(run, "save", name)
def read(name):
    try: return open(save(name)).read()
    except FileNotFoundError: return ""
today = int(datetime.date.today().strftime("%Y%m%d"))
yesterday = int((datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d"))

def session(seconds):
    s = enter_map("pltxt", "pltxtpw1", "PlTxt", log=lambda *a: None)
    st = Stream(s.map_sock, L); got = []; closed = None; t0 = time.time()
    chat(s.map_sock, "PlTxt", "@playtime")
    try:
        for pid, p in st.packets(seconds):
            for m in messages([(pid, p)]): got.append((time.time() - t0, m))
    except (ConnectionError, OSError):
        closed = time.time() - t0
    if closed is None:
        try: s.quit_game(wait=2)
        except Exception: pass
    return got, closed

ensure_account("pltxfill", "pltxtpw1")  # the first account of the stand is GM 99 (conf/GM_account.txt): exempt
time.sleep(11)  # the TXT login-server takes one registration per 10 s
ensure_account("pltxt", "pltxtpw1")
check("1 play_reset.txt holds today's date", read("play_reset.txt").startswith("%d," % today), repr(read("play_reset.txt")))
got, closed = session(70)
cid = re.search(r"^(\d+)\t\d+,\d+\tPlTxt\t", open(save("athena.txt")).read(), re.M)
srv("stop"); srv("start")
line = [l for l in read("playtime.txt").splitlines() if cid and l.startswith(cid.group(1) + ",")]
check("2 ~70 s saved as 1 minute of today", line == ["%s,1,%d" % (cid.group(1), today)] if cid else False, "lines=%s" % line)
srv("stop")
open(save("playtime.txt"), "w").write("%s,720,%d\n" % (cid.group(1), today))
srv("start")
got, closed = session(60)
lim = [t for t, m in got if "limit (12 h) reached" in m]
check("3a at the limit: the message at once", bool(lim) and lim[0] < 5, "msgs=%s" % got[-3:])
check("3b disconnected ~40 s later", bool(lim) and closed is not None and 35 <= closed - lim[0] <= 50, "closed=%s" % closed)
srv("stop")
open(save("playtime.txt"), "w").write("%s,720,%d\n" % (cid.group(1), yesterday))
srv("start")
got, closed = session(8)
pt = [m for t, m in got if "Played today" in m]
check("4 a line of yesterday counts 0", bool(pt) and "Played today: 0 h 00 min" in pt[-1] and closed is None, "pt=%s" % pt)
sys.exit(0 if ok else 1)

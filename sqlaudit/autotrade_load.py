#!/usr/bin/env python3
"""autotrade_load.py <run dir> <shops>: how fast N kept autotrade shops come back after a start.
Makes N accounts + Merchant characters with a cart (2 items) and their autotrade rows straight in the DB
(accounts 1900000000+, chars 1900000000+), starts the stand, times the restore and checks a player can log in
meanwhile; then removes all of it."""
import os, subprocess, sys, time
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
from e2elib import enter_map  # noqa: E402
SP = os.path.dirname(os.path.abspath(__file__))
run, N = sys.argv[1], int(sys.argv[2])
MY = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B"]
def sql(q): return subprocess.run(MY + ["-e", q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
def sqlf(text): subprocess.run(MY, input=text, text=True, check=True)
A0 = C0 = 1900000000
def cleanup():
    sqlf("""DELETE FROM autotrade_item WHERE char_id>=%d; DELETE FROM autotrade_shop WHERE char_id>=%d;
DELETE FROM cart_inventory WHERE char_id>=%d; DELETE FROM skill WHERE char_id>=%d; DELETE FROM `char` WHERE char_id>=%d;
DELETE FROM login WHERE account_id>=%d;
ALTER TABLE login AUTO_INCREMENT=1; ALTER TABLE `char` AUTO_INCREMENT=1;""" % (C0, C0, C0, C0, C0, A0))  # the counters back to max+1
subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
cleanup()
rows = []
for i in range(N):
    a, c = A0 + i, C0 + i
    x, y = 100 + (i % 100), 100 + (i // 100) * 2
    rows.append("INSERT INTO login (account_id,userid,user_pass,sex,email) VALUES (%d,'atl%d','x','M','a@a.com');" % (a, i))
    rows.append("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,job_level,`option`,hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) "
                "VALUES (%d,%d,0,'ATL%d',5,50,40,8,100,100,10,10,'prontera',%d,%d,'prontera',150,150);" % (c, a, i, x, y))
    rows.append("INSERT INTO skill (char_id,id,lv) VALUES (%d,1,9),(%d,36,10),(%d,39,10),(%d,41,10);" % (c, c, c, c))
    rows.append("INSERT INTO cart_inventory (char_id,nameid,amount,identify) VALUES (%d,501,10,1),(%d,512,10,1);" % (c, c))
    rows.append("INSERT INTO autotrade_shop (char_id,account_id,sex,map,x,y,dir,title,opened) VALUES (%d,%d,1,'prontera',%d,%d,0,'Shop %d',NOW());" % (c, a, x, y, i))
    rows.append("INSERT INTO autotrade_item (char_id,cart_slot,nameid,amount,price) VALUES (%d,0,501,10,100),(%d,1,512,10,50);" % (c, c))
sqlf("SET autocommit=0;\n" + "\n".join(rows) + "\nCOMMIT;\n")
print("made", N, "shops", flush=True)
out = os.path.join(run, "map.out")
n0 = open(out, errors="replace").read().count("[AUTOTRADE] restore done")
subprocess.run([os.path.join(SP, "srv.sh"), "start", run], stdout=subprocess.DEVNULL)
t_start = None
login_ok = None
while True:
    txt = open(out, errors="replace").read()
    if t_start is None and "kept shop(s) to bring back" in txt[-200000:]:
        t_start = time.time()
    if txt.count("[AUTOTRADE] restore done") > n0:
        t_end = time.time(); break
    if t_start and login_ok is None:
        t0 = time.time()
        try:
            s = enter_map("atbuy", "atpass1", "ATBuy", log=lambda *a: None); s.quit_game(wait=1)
            login_ok = time.time() - t0
        except Exception as e:
            login_ok = "failed: %s" % e
    time.sleep(0.2)
back = txt.count("back on prontera") - 0
print("restore: %d shops in %.1f s (%.0f/s); a player login meanwhile took %s s" % (N, t_end - t_start, N / max(0.1, t_end - t_start),
      "%.1f" % login_ok if isinstance(login_ok, float) else login_ok), flush=True)
online = sql("SELECT COUNT(*) FROM `char` WHERE char_id>=%d AND online=1" % C0)
print("restored vendors with char.online=1:", online)
print("shops back (log lines, all runs):", open(out, errors="replace").read().count("back on prontera"))
time.sleep(125)
st = [l for l in open(os.path.join(run, "char.out"), errors="replace").read().splitlines() if "Online status" in l or "Online reconcile" in l]
print("char-server:", st[-1] if st else None)
subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
print("saved:", [l for l in open(out, errors="replace").read().splitlines() if "[AUTOTRADE] saved" in l][-1])
cleanup()

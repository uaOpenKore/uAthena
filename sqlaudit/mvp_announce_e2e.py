#!/usr/bin/env python3
"""mvp_announce_e2e.py <e2e run dir>: a spawned MVP's death is announced to every player with its respawn time
(S. 2026-11-23: "серверная рассылка, и чтобы клиент подхватывал таймер"). On the e2e stand (ports 6900.., the local
`ragnarok` DB). A GM stands in prt_maze03 (Baphomet's spawn), a second player in prontera:
 1 @killmonster in prt_maze03 -> the player in ANOTHER map gets the 0x9a broadcast
   "[MVP] Baphomet was defeated on prt_maze03. Back in H:MM:SS."
 2 the time is the server's respawn timer: Baphomet 1039,1,7200000,3600000 -> max(spawn+2h, death+1h) = ~2:00:00
 3 the Baby Baphomets (no MVP exp) killed with it are not announced"""
import re, struct, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/e2e/tools")
import rostub  # noqa: E402
from elemark_e2e import Stream, load_lengths  # noqa: E402
run = sys.argv[1]
MY = ["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-N", "-B"]
def sql(q): return subprocess.run(MY + ["-e", q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
def srv(a): subprocess.run(["bash", SCR + "/e2e/tools/srv.sh", a, run], stdout=subprocess.DEVNULL)
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
L = load_lengths("/root/BornRok/src/net/PacketTable.cpp")
ACC = [(900410000, "mvpgm", "MvpGm", "prt_maze03", 99), (900410001, "mvpwatch", "MvpWatch", "prontera", 0)]
def wipe():
    for a, _, _, _, _ in ACC:
        sql("DELETE FROM `char` WHERE char_id=%d; DELETE FROM login WHERE account_id=%d" % (a, a))
srv("stop"); wipe()
for a, u, n, m, lv in ACC:
    sql("INSERT INTO login (account_id,userid,user_pass,sex,email,level) VALUES (%d,'%s','mvppw1','M','a@a.com',%d)" % (a, u, lv))
    sql("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,job_level,hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) "
        "VALUES (%d,%d,0,'%s',0,99,50,9000,9000,500,500,'%s',100,100,'prontera',150,150)" % (a, a, n, m))
try:
    srv("start"); time.sleep(3)
    ss = []
    for a, u, n, m, lv in ACC:
        s = rostub.Session(u, "mvppw1", log=lambda *x: None); s.login(); s.char_enter(); s.select_char(0)
        assert s.map_enter()[0] == "ok"; ss.append(s)
    gm, watch = ss
    gst, wst = Stream(gm.map_sock, L), Stream(watch.map_sock, L)
    list(gst.packets(2)); list(wst.packets(1))
    msg = ("MvpGm : @killmonster").encode("latin-1") + b"\0"
    gm.map_sock.sendall(struct.pack("<HH", 0xF3, 4 + len(msg)) + msg)
    bc = []
    for pid, p in wst.packets(6):
        if pid == 0x9a: bc.append(p[4:].split(b"\0")[0].decode("latin-1"))
    mvp = [x for x in bc if x.startswith("[MVP]")]
    m = re.match(r"\[MVP\] (.+) was defeated on (\S+)\. Back in (\d+):(\d\d):(\d\d)\.$", mvp[0]) if mvp else None
    check("1 the player in another map gets the MVP broadcast", bool(m) and m.group(1) == "Baphomet" and m.group(2) == "prt_maze03",
          "broadcasts=%s" % bc)
    left = int(m.group(3)) * 3600 + int(m.group(4)) * 60 + int(m.group(5)) if m else -1
    check("2 the respawn time is the server's (~2:00:00 for a boss killed right after spawn)", 7100 <= left <= 7200, "left=%d s" % left)
    check("3 only the MVP is announced (no Baphomet Jr.)", len(mvp) == 1, "mvp lines=%s" % mvp)
    for s in ss:
        try: s.quit_game(wait=1)
        except Exception: pass
finally:
    srv("stop"); wipe()
    sql("ALTER TABLE login AUTO_INCREMENT=1; ALTER TABLE `char` AUTO_INCREMENT=1")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)

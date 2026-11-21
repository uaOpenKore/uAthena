#!/usr/bin/env python3
"""onlinestat_e2e.py <run dir>: the char-server's online statistics (S. 2026-11-21) on the SQL stand.
The char-server samples who is on a map every minute and its worker writes the sums to log/online_spool.jsonl every
onlinestat_interval (15 s here), then into MongoDB uaro_test.online_daily (127.0.0.1:27917, the local test mongod)
and empties the file. Without that mongod the file just grows (and the checks read the file).
 1 a player on the map ~140 s: 2-3 online minutes of today, with its name
 2 @buyplaytime 5: paid_buy 5
 3 @autopay on ~2 minutes: paid_auto >= 1
 4 an autotrade shop is not online: the vendor gets no minutes while it is a shop
 5 Mongo down: the minutes wait in the file, the char-server says so (once a try)
 6 a char-server restart keeps the file (nothing lost) and the next minutes add to it
 with Mongo: 7 the documents hold the same sums, 8 the file is empty, 9 the TTL index (365 days) and the date
"""
import datetime, json, os, struct, subprocess, sys, time
SP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths, messages  # noqa: E402
run = sys.argv[1]
MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
MONGO = os.environ.get("ONLINESTAT_MONGO", "mongodb://127.0.0.1:27917/")  # ...:27918 (nothing there) = Mongo down
L = load_lengths()
POT, APPLE = 501, 512
def sql(q): return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def charlog(): return open(os.path.join(run, "char.out"), errors="replace").read()
def stop(): subprocess.run([os.path.join(SP, "srv.sh"), "stop", run], stdout=subprocess.DEVNULL)
def start():
    subprocess.run([os.path.join(SP, "srv.sh"), "start", run], stdout=subprocess.DEVNULL)
    end = time.time() + 60
    while time.time() < end and "online after" not in subprocess.run(["tail", "-c", "4000", os.path.join(run, "map.out")],
                                                                    stdout=subprocess.PIPE, text=True).stdout:
        time.sleep(1)
    time.sleep(3)
def cid(name): return sql("SELECT char_id FROM `char` WHERE name='%s'" % name)
SPOOL = os.path.join(run, "log", "online_spool.jsonl")
# the worktree's conf/mongo_athena.conf, and the credentials file it imports (conf/mongo_conf.txt)
SRC_CONF = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/tick64/conf/mongo_athena.conf"
CONF = os.path.join(run, "conf", "mongo_conf.txt")
def conf(on):
    subprocess.run(["cp", SRC_CONF, os.path.join(run, "conf", "mongo_athena.conf")])
    if on:
        open(CONF, "w").write("onlinestat_mongo_uri: %s\nonlinestat_mongo_db: uaro_test\nonlinestat_interval: 15\n" % MONGO)
    else:
        try: os.remove(CONF)
        except FileNotFoundError: pass
def mongo():
    try:
        import pymongo
        c = pymongo.MongoClient(MONGO, serverSelectionTimeoutMS=2000); c.admin.command("ping")
        return c
    except Exception:
        return None
def spool_sums():
    out = {}
    try:
        for line in open(SPOOL, encoding="utf-8"):
            d = json.loads(line)
            k = (d["d"], d["c"]); s = out.setdefault(k, {"name": "", "o": 0, "b": 0, "p": 0})
            if d["n"]: s["name"] = d["n"]
            for f in "obp": s[f] += d[f]
    except FileNotFoundError:
        pass
    return out

class Client:
    def __init__(self, user, pw, name):
        self.name = name
        self.s = enter_map(user, pw, name, log=lambda *a: None)
        self.st = Stream(self.s.map_sock, L); self.pk = []; self.msgs = []
    def pump(self, sec):
        try:
            for pid, p in self.st.packets(sec):
                self.pk.append((pid, p)); self.msgs += messages([(pid, p)])
        except (ConnectionError, OSError):
            pass
    def send(self, b): self.s.map_sock.sendall(b)
    def cmd(self, t): chat(self.s.map_sock, self.name, t)
    def quit(self):
        try: self.s.quit_game(wait=2)
        except Exception: pass

today = int(time.strftime("%Y%m%d"))
mc = mongo()
print("MongoDB at %s: %s" % (MONGO, "up" if mc else "not running (the checks read the spool file)"), flush=True)
if mc: mc.uaro_test.online_daily.drop()
try:
    stop(); conf(True)
    try: os.remove(SPOOL)
    except FileNotFoundError: pass
    start()
    for u, pw, n in (("atvend", "atpass1", "ATVend"), ("osbuy", "ospass1", "OSBuy")):
        if sql("SELECT COUNT(*) FROM login WHERE userid='%s'" % u) == "0":
            try: rostub.Session(u + "_M", pw, log=lambda *a: None).login()
            except Exception: pass
            time.sleep(0.5)
        if not cid(n):
            s = enter_map(u, pw, n, log=lambda *a: None); s.quit_game(wait=2)
    time.sleep(3); stop()
    v, b = cid("ATVend"), cid("OSBuy")
    # the vendor (like autotrade_e2e): Merchant with Vending and a cart at prontera 150,150
    sql("UPDATE login SET level=0 WHERE userid IN ('atvend','osbuy')")
    sql("UPDATE `char` SET class=5, job_level=40, base_level=50, `option`=8, zeny=1000, last_map='prontera', last_x=150, last_y=150, online=0 WHERE char_id=%s" % v)
    sql("REPLACE INTO skill (char_id, id, lv) VALUES (%s, 1, 9), (%s, 36, 10), (%s, 37, 10), (%s, 39, 10), (%s, 41, 10)" % (v, v, v, v, v))
    sql("DELETE FROM cart_inventory WHERE char_id=%s" % v)
    sql("INSERT INTO cart_inventory (char_id, nameid, amount, identify) VALUES (%s, %d, 50, 1), (%s, %d, 30, 1)" % (v, POT, v, APPLE))
    sql("DELETE FROM autotrade_shop WHERE char_id=%s" % v); sql("DELETE FROM autotrade_item WHERE char_id=%s" % v)
    # the player: 100 minutes played today, zeny for @buyplaytime / @autopay
    now = datetime.datetime.now()
    sql("REPLACE INTO play_reset (id, reset_date, reset_at) VALUES (0, %d, FROM_UNIXTIME(%d))" % (today, int((now - datetime.timedelta(hours=1)).timestamp())))
    sql("UPDATE `char` SET base_level=10, zeny=100000, play_minutes=100, play_date=%d, last_map='prontera', last_x=152, last_y=150, online=0 WHERE char_id=%s" % (today, b))
    sql("DELETE FROM global_reg_value WHERE str='PLAY_AUTOPAY'")
    start()
    vend = Client("atvend", "atpass1", "ATVend"); vend.pump(2)
    items = struct.pack("<HHI", 2, 50, 100) + struct.pack("<HHI", 3, 30, 50)
    vend.send(struct.pack("<HH80sB", 0x1b2, 85 + len(items), b"onlinestat shop", 1) + items); vend.pump(2)
    vend.cmd("@autotrade"); vend.pump(2)
    shop = sql("SELECT COUNT(*) FROM autotrade_shop WHERE char_id=%s" % v) == "1"
    buy = Client("osbuy", "ospass1", "OSBuy"); buy.pump(2)
    buy.cmd("@buyplaytime 5"); buy.pump(2)
    buy.cmd("@autopay on"); buy.pump(2)
    t0 = time.time()
    while time.time() - t0 < 140:
        buy.pump(5)
    buy.cmd("@autopay off"); buy.pump(2); buy.quit()
    time.sleep(25)  # one worker round (15 s) after the last minute
    def sums():
        if mc:
            d = {}
            for doc in mc.uaro_test.online_daily.find():
                d[(int(doc["date"].replace("-", "")), doc["char_id"])] = {"name": doc.get("name", ""), "o": doc["online"],
                                                                         "b": doc["paid_buy"], "p": doc["paid_auto"]}
            return d
        return spool_sums()
    s = sums(); me = s.get((today, int(b)), {}); vs = s.get((today, int(v)), {})
    check("1 ~140 s on the map: 2-3 online minutes of today, with the name", 2 <= me.get("o", 0) <= 3 and me.get("name") == "OSBuy", "me=%s" % me)
    check("2 @buyplaytime 5: paid_buy 5", me.get("b") == 5, "me=%s" % me)
    check("3 @autopay ~2 minutes: paid_auto >= 1", me.get("p", 0) >= 1, "me=%s" % me)
    check("4 an autotrade shop gets no online minutes (at most the one sampled before @autotrade)", shop and vs.get("o", 0) <= 1, "shop=%s vendor=%s" % (shop, vs))
    if not mc:
        check("5 Mongo down: the minutes wait in the file and the char-server says so",
              os.path.getsize(SPOOL) > 0 and "MongoDB not reached" in charlog(), "size=%s" % os.path.getsize(SPOOL))
    before = sums()
    stop(); start()
    buy = Client("osbuy", "ospass1", "OSBuy")
    t0 = time.time()
    while time.time() - t0 < 75:
        buy.pump(5)
    buy.quit(); time.sleep(25)
    after = sums(); m2 = after.get((today, int(b)), {})
    check("6 a char-server restart loses nothing and the next minutes add up",
          m2.get("o", 0) >= me.get("o", 0) + 1 and m2.get("b") == 5 and m2.get("p", 0) == me.get("p", 0), "before=%s after=%s" % (me, m2))
    if mc:
        sp = spool_sums()
        check("7 the documents are the sums (and were written by $inc across rounds)", m2.get("o", 0) >= 3, "doc=%s" % m2)
        check("8 the file is empty once Mongo took it", not sp, "spool=%s" % sp)
        idx = mc.uaro_test.online_daily.index_information()
        doc = mc.uaro_test.online_daily.find_one({"char_id": int(b)})
        midnight = datetime.datetime.strptime(str(today), "%Y%m%d")
        check("9 TTL index on day, 365 days; _id, date and day of the document",
              idx.get("ttl_day", {}).get("expireAfterSeconds") == 31536000 and doc["_id"] == "%d:%s" % (today, b)
              and doc["date"] == midnight.strftime("%Y-%m-%d")
              and abs(doc["day"].replace(tzinfo=datetime.timezone.utc).timestamp() - midnight.timestamp()) < 1,
              "idx=%s doc=%s" % (list(idx), doc))
finally:
    stop(); conf(False)
    sql("DELETE FROM autotrade_shop WHERE char_id=%s" % (cid("ATVend") or 0)); sql("DELETE FROM autotrade_item WHERE char_id=%s" % (cid("ATVend") or 0))
    sql("DELETE FROM global_reg_value WHERE str='PLAY_AUTOPAY'")
    sql("ALTER TABLE login AUTO_INCREMENT=1; ALTER TABLE `char` AUTO_INCREMENT=1")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""idcompact_e2e.py <run dir>: dense ids at the char-server's start (S. 2026-11-22).
Runs only the char-server of <run dir> against its own database (the isolated MariaDB on 13306,
ragnarok_idc: a copy of the stand DB), so the renumbering never touches the other stands. Data with gaps:
accounts 2000100/2000300, characters 150500/150900 (married), a guild (master 150900, member 150500) with an
alliance to a second guild, a party, a hatched pet and an egg in storage, a homunculus with a skill, item rows
with big ids, an item forged by 150900 in 150500's bag, friends, variables; plus dangling rows (items of a missing
character, a friend that no longer exists, a spouse id of nobody).
 1 mode 1 (report): nothing changes, the log tells the counts
 2 mode 2: every id kind dense from its first number in its old order, and every reference follows
 3 the forged item's maker and the egg's pet id follow; dangling rows deleted, the dangling spouse set to 0
 4 AUTO_INCREMENT = MAX+1 in the tables (login, char, guild, party, pet, homunculus, inventory, storage)
 5 a second start has nothing to move"""
import os, subprocess, sys, time, signal
run = sys.argv[1]
CONF = os.path.join(run, "conf", "char_athena.conf")
MARK_B, MARK_E = "// IDCOMPACT_E2E BEGIN", "// IDCOMPACT_E2E END"
MY = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok_idc", "-N", "-B"]
def sql(q): return subprocess.run(MY + ["-e", q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
def one(q):
    r = sql(q)
    return r.split("\n")[0] if r else ""
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c
def lohi(v): return (v & 0xFFFF) - (0x10000 if v & 0x8000 else 0), ((v >> 16) & 0xFFFF) - (0x10000 if v & 0x80000000 else 0)

def set_mode(m):
    conf = open(CONF).read()
    if MARK_B in conf:
        conf = conf[:conf.index(MARK_B)] + conf[conf.index(MARK_E) + len(MARK_E) + 1:]
    if m is not None:
        conf += "%s\nid_compact_mode: %d\naccount_archive_mode: 0\n%s\n" % (MARK_B, m, MARK_E)
    open(CONF, "w").write(conf)

def run_char(m, secs=12):
    set_mode(m)
    out = open(os.path.join(run, "char.out"), "w")
    p = subprocess.Popen(["./char-server_sql"], cwd=run, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.time() + 60
    while time.time() < deadline:
        time.sleep(1)
        txt = open(os.path.join(run, "char.out"), errors="replace").read()
        if "[IDCOMPACT] done" in txt or "report only: nothing" in txt or "nothing changed" in txt or "Finished initilizing" in txt or p.poll() is not None:
            time.sleep(1)
            break
    os.killpg(p.pid, signal.SIGTERM)
    try: p.wait(10)
    except Exception: os.killpg(p.pid, signal.SIGKILL)
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", open(os.path.join(run, "char.out"), errors="replace").read())

A1, A2 = 2000100, 2000300
C1, C2 = 150500, 150900
G1, G2, P1, PET1, PET2, H1 = 50, 60, 70, 400, 410, 300
sql("DELETE FROM login WHERE account_id IN (%d,%d)" % (A1, A2))
sql("DELETE FROM `char` WHERE char_id IN (%d,%d)" % (C1, C2))
sql("INSERT INTO login (account_id,userid,user_pass,sex,email,lastlogin) VALUES (%d,'idcA','pw','M','a@a.com',NOW()),(%d,'idcB','pw','F','a@a.com',NOW())" % (A1, A2))
CH = ("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,guild_id,party_id,partner_id,pet_id,homun_id,"
      "last_map,last_x,last_y,save_map,save_x,save_y) VALUES ")
sql(CH + "(%d,%d,0,'IdcOne',1,10,%d,%d,%d,%d,0,'prontera',150,150,'prontera',150,150),(%d,%d,0,'IdcTwo',18,50,%d,%d,%d,0,%d,'prontera',150,150,'prontera',150,150)"
    % (C1, A1, G1, P1, C2, PET1, C2, A2, G1, P1, C1, H1))
sql("INSERT INTO `char` (char_id,account_id,char_num,name,class,partner_id,last_map,save_map) VALUES (150950,%d,1,'IdcLone',1,199998,'prontera','prontera')" % A2)
sql("INSERT INTO guild (guild_id,name,char_id,master,guild_lv,max_member) VALUES (%d,'IdcG',%d,'IdcTwo',1,16),(%d,'IdcG2',%d,'IdcOne',1,16)" % (G1, C2, G2, C1))
sql("INSERT INTO guild_member (guild_id,account_id,char_id,name,position) VALUES (%d,%d,%d,'IdcTwo',0),(%d,%d,%d,'IdcOne',1)" % (G1, A2, C2, G1, A1, C1))
sql("INSERT INTO guild_alliance (guild_id,opposition,alliance_id,name) VALUES (%d,0,%d,'IdcG2'),(%d,0,%d,'IdcG')" % (G1, G2, G2, G1))
sql("INSERT INTO party (party_id,name,leader_id,leader_char) VALUES (%d,'IdcP',%d,%d)" % (P1, A2, C2))
sql("INSERT INTO pet (pet_id,class,name,account_id,char_id,level,egg_id,incuvate) VALUES (%d,1002,'IdcPetOut',%d,%d,1,9001,0),(%d,1002,'IdcPetEgg',%d,%d,1,9001,1)" % (PET1, A1, C1, PET2, A1, C1))
sql("INSERT INTO homunculus (homun_id,char_id,class,name,level) VALUES (%d,%d,6001,'IdcHom',10)" % (H1, C2))
sql("INSERT INTO skill_homunculus (homun_id,id,lv) VALUES (%d,8001,2)" % H1)
m2, m3 = lohi(C2); e1, e2 = lohi(PET2)
sql("INSERT INTO inventory (id,char_id,nameid,amount,identify,card0,card2,card3) VALUES (90000,%d,1201,1,1,255,%d,%d),(90500,%d,501,3,1,0,0,0),(91000,199999,502,1,1,0,0,0)" % (C1, m2, m3, C2))
sql("INSERT INTO storage (id,account_id,nameid,amount,identify,card0,card1,card2) VALUES (70000,%d,9001,1,1,-256,%d,%d)" % (A1, e1, e2))
sql("INSERT INTO friends (char_id,friend_account,friend_id) VALUES (%d,%d,%d),(%d,%d,199997)" % (C1, A2, C2, C1, A2))
sql("INSERT INTO global_reg_value (char_id,str,value,type,account_id) VALUES (0,'IDC_ACC','5',2,%d),(%d,'IDC_CHR','6',3,%d)" % (A1, C2, A2))
sql("INSERT INTO skill (char_id,id,lv) VALUES (%d,228,10)" % C2)

def expected(table, col, base, keep_below=False):
    ids = [int(x) for x in sql("SELECT `%s` FROM `%s` ORDER BY `%s`" % (col, table, col)).split()]
    nxt = base if keep_below or not ids or ids[0] >= base else ids[0]
    m = {}
    for i in ids:
        if keep_below and i < base:
            m[i] = i
        else:
            m[i] = nxt; nxt += 1
    return m
# dangling rows go before the renumbering: the maps are taken from the rows that stay
EA = expected("login", "account_id", 2000000, True); EC = expected("char", "char_id", 150000)
EG = expected("guild", "guild_id", 1); EP = expected("party", "party_id", 1); EPET = expected("pet", "pet_id", 1)
EH = expected("homunculus", "homun_id", 1)
sql("DELETE FROM inventory WHERE id=91000")  # what the compaction will delete: the inventory map without it
EINV = expected("inventory", "id", 1)
sql("INSERT INTO inventory (id,char_id,nameid,amount,identify) VALUES (91000,199999,502,1,1)")
snapshot = sql("SELECT char_id,account_id,guild_id,party_id,partner_id,pet_id,homun_id FROM `char` ORDER BY char_id")
try:
    log1 = run_char(1)
    check("1 report: nothing changed, the log has the counts",
          sql("SELECT char_id,account_id,guild_id,party_id,partner_id,pet_id,homun_id FROM `char` ORDER BY char_id") == snapshot
          and "report only: nothing changed" in log1 and "inventory.char_id: 1 rows point at chr ids that do not exist -> deleted" in log1,
          "\n".join(l for l in log1.split("\n") if "IDCOMPACT" in l)[-1500:])
    log2 = run_char(2)
    nC1, nC2, nA1, nA2 = EC[C1], EC[C2], EA[A1], EA[A2]
    row1 = sql("SELECT account_id,guild_id,party_id,partner_id,pet_id FROM `char` WHERE char_id=%d AND name='IdcOne'" % nC1)
    row2 = sql("SELECT account_id,guild_id,party_id,partner_id,homun_id FROM `char` WHERE char_id=%d AND name='IdcTwo'" % nC2)
    lone = one("SELECT partner_id FROM `char` WHERE name='IdcLone'")
    dense = {t: one("SELECT COUNT(*) = MAX(`%s`) - MIN(`%s`) + 1 FROM `%s`%s" % (c, c, t, w)) for t, c, w in
             (("char", "char_id", ""), ("guild", "guild_id", ""), ("party", "party_id", ""), ("pet", "pet_id", ""),
              ("homunculus", "homun_id", ""), ("inventory", "id", ""), ("storage", "id", ""), ("login", "account_id", " WHERE account_id >= 2000000"))}
    refs = dict(
        r1=row1, r2=row2,
        gm=sql("SELECT char_id, account_id FROM guild_member WHERE guild_id=%d ORDER BY char_id" % EG[G1]),
        gmaster=one("SELECT char_id FROM guild WHERE guild_id=%d AND name='IdcG'" % EG[G1]),
        ally=sql("SELECT guild_id, alliance_id FROM guild_alliance WHERE guild_id IN (%d,%d) ORDER BY guild_id" % (EG[G1], EG[G2])),
        party=one("SELECT CONCAT(leader_id,'/',leader_char) FROM party WHERE party_id=%d" % EP[P1]),
        pet=sql("SELECT pet_id, account_id, char_id FROM pet WHERE name LIKE 'IdcPet%' ORDER BY name"),
        hom=one("SELECT char_id FROM homunculus WHERE homun_id=%d" % EH[H1]), homsk=one("SELECT lv FROM skill_homunculus WHERE homun_id=%d" % EH[H1]),
        friends=sql("SELECT char_id, friend_account, friend_id FROM friends WHERE char_id=%d" % nC1),
        regs=sql("SELECT str, char_id, account_id FROM global_reg_value WHERE str LIKE 'IDC_%' ORDER BY str"),
        skill=one("SELECT lv FROM skill WHERE char_id=%d AND id=228" % nC2), dense=dense, lone=lone)
    exp_ok = (row1 == "%d\t%d\t%d\t%d\t%d" % (nA1, EG[G1], EP[P1], nC2, EPET[PET1]) and row2 == "%d\t%d\t%d\t%d\t%d" % (nA2, EG[G1], EP[P1], nC1, EH[H1])
              and refs["gm"] == "%d\t%d\n%d\t%d" % tuple(sorted([(nC1, nA1), (nC2, nA2)])[0] + sorted([(nC1, nA1), (nC2, nA2)])[1])
              and refs["gmaster"] == str(nC2) and refs["ally"] == "%d\t%d\n%d\t%d" % ((EG[G1], EG[G2], EG[G2], EG[G1]) if EG[G1] < EG[G2] else (EG[G2], EG[G1], EG[G1], EG[G2]))
              and refs["party"] == "%d/%d" % (nA2, nC2)
              and refs["pet"] == "%d\t%d\t%d\n%d\t%d\t%d" % (EPET[PET2], nA1, nC1, EPET[PET1], nA1, nC1)
              and refs["hom"] == str(nC2) and refs["homsk"] == "2" and refs["friends"] == "%d\t%d\t%d" % (nC1, nA2, nC2)
              and refs["regs"] == "IDC_ACC\t0\t%d\nIDC_CHR\t%d\t%d" % (nA1, nC2, nA2) and refs["skill"] == "10")
    check("2 ids dense in their old order, every reference follows", exp_ok and set(dense.values()) == {"1"}, str(refs) + "\n" + "\n".join(l for l in log2.split("\n") if "IDCOMPACT" in l)[-2000:])
    n2, n3 = lohi(nC2); p1, p2 = lohi(EPET[PET2])
    forged = one("SELECT COUNT(*) FROM inventory WHERE char_id=%d AND card0=255 AND card2=%d AND card3=%d AND id=%d" % (nC1, n2, n3, EINV[90000]))
    egg = one("SELECT COUNT(*) FROM storage WHERE account_id=%d AND card0=-256 AND card1=%d AND card2=%d" % (nA1, p1, p2))
    check("3 maker + egg ids follow; dangling rows deleted, dangling spouse 0",
          forged == "1" and egg == "1" and one("SELECT COUNT(*) FROM inventory WHERE char_id=199999") == "0"
          and one("SELECT COUNT(*) FROM friends WHERE friend_id=199997") == "0" and lone == "0",
          "forged=%s egg=%s lone=%s" % (forged, egg, lone))
    ai = {}
    for t, c in (("login", "account_id"), ("char", "char_id"), ("guild", "guild_id"), ("party", "party_id"), ("pet", "pet_id"),
                 ("homunculus", "homun_id"), ("inventory", "id"), ("storage", "id")):
        ai[t] = (one("SELECT AUTO_INCREMENT FROM information_schema.tables WHERE table_schema='ragnarok_idc' AND table_name='%s'" % t),
                 one("SELECT MAX(`%s`)+1 FROM `%s`" % (c, t)))
    check("4 AUTO_INCREMENT = MAX+1", all(a == b for a, b in ai.values()), str(ai))
    log3 = run_char(2)
    check("5 a second start moves nothing", "0 rows rewritten" in log3, "\n".join(l for l in log3.split("\n") if "IDCOMPACT" in l)[-800:])
finally:
    set_mode(None)
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)

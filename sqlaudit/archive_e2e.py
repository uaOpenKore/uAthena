#!/usr/bin/env python3
"""archive_e2e.py <e2e run dir>: inactive accounts into the archive and back on a login (S. 2026-11-22).
On the e2e stand (ports 6900.., the local `ragnarok` DB). The run dir's char_athena.conf gets a marker block:
account_archive_mode 2, 365 days, any hour, every 5 s.
Accounts:
  OLD   last login 2024: char ArcMaster = guild master (a member from FRESH), married to FRESH's char, a forged
        item made by itself, a pet egg, a hatched pet... homunculus with a skill, storage, account + char variables
  FRESH logged in today: char ArcSpouse (in the guild, the spouse, OLD's char on its friend list, a wedding ring)
  NEVER never logged in, no registration date (from before login.created): archived
  NEWREG never logged in, registered today: stays
  BUSY  last login 2024, at the character select during the run: stays (online)
Checks:
 1 OLD and NEVER archived (arc_index state 1, rows in arc_*), gone from the live tables; NEWREG, FRESH, BUSY stay
 2 the guild is broken, the spouse divorced (no ring), OLD's char left FRESH's friend list
 3 a wrong password for OLD: refused, the archive is untouched
 4 registering OLD's login name (_M) is refused; a new character with an archived name is refused
 5 the right password: logged in with a NEW account id, the character select lists ArcMaster (a new char id)
 6 the restored character: no guild/party/spouse; its items, skill, variables, storage, pet, homunculus back
   with new pet/homunculus ids; the forged item's maker and the egg's pet id rewritten; arc rows gone, state 2"""
import os, struct, subprocess, sys, time
SCR = "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad"
sys.path.insert(0, SCR + "/e2e/tools")
import rostub  # noqa: E402
run = sys.argv[1]
CONF = os.path.join(run, "conf", "char_athena.conf")
MARK_B, MARK_E = "// ARCHIVE_E2E BEGIN", "// ARCHIVE_E2E END"
MY = ["mysql", "--no-defaults", "-h127.0.0.1", "-uragnarok", "-pragnarok", "ragnarok", "-N", "-B"]
def sql(q): return subprocess.run(MY + ["-e", q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()
def one(q):
    r = sql(q)
    return r.split("\n")[0] if r else ""
def srv(a): subprocess.run(["bash", SCR + "/e2e/tools/srv.sh", a, run], stdout=subprocess.DEVNULL)
ok = True
def check(n, c, d=""):
    global ok
    print("%s  %s%s" % ("ok  " if c else "FAIL", n, ("  [%s]" % d) if d and not c else ""), flush=True); ok = ok and c

OLD, FRESH, NEVER, NEWREG, BUSY = 900500001, 900500002, 900500003, 900500004, 900500005
C_OLD, C_FRESH, C_BUSY = 900500001, 900500002, 900500005
GUILD, PET_EGG, PET_HATCHED, HOM = 900500001, 900500001, 900500002, 900500001
AIDS = "%d,%d,%d,%d,%d" % (OLD, FRESH, NEVER, NEWREG, BUSY)
CIDS = "%d,%d,%d" % (C_OLD, C_FRESH, C_BUSY)
def lohi(v): return (v & 0xFFFF) - (0x10000 if v & 0x8000 else 0), ((v >> 16) & 0xFFFF) - (0x10000 if v & 0x8000_0000 else 0)

def cleanup():
    tabs = sql("SHOW TABLES LIKE 'arc\\_%'").split()
    for t in tabs:
        sql("DROP TABLE `%s`" % t)
    sql("DELETE FROM login WHERE account_id IN (%s) OR userid IN ('arcold','arcfresh','arcnever','arcnewreg','arcbusy')" % AIDS)
    sql("DELETE FROM `char` WHERE account_id IN (%s) OR name IN ('ArcMaster','ArcSpouse','ArcBusy','ArcMaster2')" % AIDS)
    for t in ("inventory", "cart_inventory", "skill", "friends", "memo", "hotkey", "quest", "achievement", "sc_data"):
        sql("DELETE FROM `%s` WHERE char_id IN (%s) OR char_id >= 900500000" % (t, CIDS))
    sql("DELETE FROM storage WHERE account_id IN (%s) OR account_id >= 900500000" % AIDS)
    sql("DELETE FROM global_reg_value WHERE account_id IN (%s) OR char_id IN (%s) OR str LIKE 'ARCE2E%%'" % (AIDS, CIDS))
    sql("DELETE FROM pet WHERE pet_id IN (%d,%d) OR name LIKE 'ArcPet%%'" % (PET_EGG, PET_HATCHED))
    sql("DELETE FROM skill_homunculus WHERE homun_id IN (SELECT homun_id FROM homunculus WHERE name = 'ArcHom')")
    sql("DELETE FROM homunculus WHERE name = 'ArcHom'")
    for t in ("guild", "guild_member", "guild_position", "guild_skill", "guild_storage"):
        sql("DELETE FROM `%s` WHERE guild_id = %d" % (t, GUILD))
    conf = open(CONF).read()
    if MARK_B in conf:
        conf = conf[:conf.index(MARK_B)] + conf[conf.index(MARK_E) + len(MARK_E) + 1:]
        open(CONF, "w").write(conf)

srv("stop")
cleanup()
open(CONF, "a").write("%s\naccount_archive_mode: 2\naccount_archive_days: 365\naccount_archive_hour: -1\n"
                      "account_archive_batch: 10\naccount_archive_interval: 5\n%s\n" % (MARK_B, MARK_E))
L = "INSERT INTO login (account_id,userid,user_pass,sex,email,lastlogin,created) VALUES "
sql(L + "(%d,'arcold','oldpw1','M','a@a.com','2024-01-01 10:00:00',NULL),(%d,'arcfresh','frpw1','F','a@a.com',NOW(),NULL),"
        "(%d,'arcnever','nvpw1','M','a@a.com','0000-00-00 00:00:00',NULL),(%d,'arcnewreg','nrpw1','M','a@a.com','0000-00-00 00:00:00',NOW()),"
        "(%d,'arcbusy','bspw1','M','a@a.com','2024-01-01 10:00:00',NULL)" % (OLD, FRESH, NEVER, NEWREG, BUSY))
CH = ("INSERT INTO `char` (char_id,account_id,char_num,name,class,base_level,job_level,guild_id,partner_id,pet_id,homun_id,"
      "hp,max_hp,sp,max_sp,last_map,last_x,last_y,save_map,save_x,save_y) VALUES ")
sql(CH + "(%d,%d,0,'ArcMaster',18,70,40,%d,%d,%d,%d,500,500,100,100,'prontera',150,150,'prontera',150,150),"
         "(%d,%d,0,'ArcSpouse',4,60,40,%d,%d,0,0,500,500,100,100,'prontera',150,150,'prontera',150,150),"
         "(%d,%d,0,'ArcBusy',1,10,10,0,0,0,0,50,50,10,10,'prontera',150,150,'prontera',150,150)"
    % (C_OLD, OLD, GUILD, C_FRESH, PET_HATCHED, HOM, C_FRESH, FRESH, GUILD, C_OLD, C_BUSY, BUSY))
sql("INSERT INTO guild (guild_id,name,char_id,master,guild_lv,max_member) VALUES (%d,'ArcGuild',%d,'ArcMaster',1,16)" % (GUILD, C_OLD))
sql("INSERT INTO guild_member (guild_id,account_id,char_id,name,position) VALUES (%d,%d,%d,'ArcMaster',0),(%d,%d,%d,'ArcSpouse',1)"
    % (GUILD, OLD, C_OLD, GUILD, FRESH, C_FRESH))
sql("INSERT INTO guild_position (guild_id,position,name,mode) VALUES (%d,0,'Master',17),(%d,1,'Member',0)" % (GUILD, GUILD))
c2, c3 = lohi(C_OLD); e1, e2 = lohi(PET_EGG)
sql("INSERT INTO inventory (char_id,nameid,amount,identify,card0,card1,card2,card3) VALUES "
    "(%d,1201,1,1,255,0,%d,%d),(%d,9001,1,1,-256,%d,%d,0),(%d,501,5,1,0,0,0,0),(%d,2634,1,1,0,0,0,0)"
    % (C_OLD, c2, c3, C_OLD, e1, e2, C_OLD, C_FRESH))  # 2634 = a wedding ring on the spouse
sql("INSERT INTO storage (account_id,nameid,amount,identify,card0,card1,card2,card3) VALUES (%d,1201,1,1,255,0,%d,%d),(%d,502,7,1,0,0,0,0)"
    % (OLD, c2, c3, OLD))
sql("INSERT INTO skill (char_id,id,lv) VALUES (%d,228,10)" % C_OLD)
sql("INSERT INTO friends (char_id,friend_account,friend_id) VALUES (%d,%d,%d),(%d,%d,%d)" % (C_FRESH, OLD, C_OLD, C_OLD, FRESH, C_FRESH))
sql("INSERT INTO global_reg_value (char_id,str,value,type,account_id) VALUES (0,'ARCE2E_ACC','11',2,%d),(%d,'ARCE2E_CHR','22',3,%d)" % (OLD, C_OLD, OLD))
sql("INSERT INTO pet (pet_id,class,name,account_id,char_id,level,egg_id,intimate,hungry,incuvate) VALUES "
    "(%d,1002,'ArcPetEgg',%d,%d,1,9001,250,100,1),(%d,1002,'ArcPetOut',%d,%d,1,9001,250,100,0)" % (PET_EGG, OLD, C_OLD, PET_HATCHED, OLD, C_OLD))
sql("INSERT INTO homunculus (homun_id,char_id,class,name,level,hp,max_hp,sp,max_sp,alive) VALUES (%d,%d,6001,'ArcHom',10,100,100,50,50,1)" % (HOM, C_OLD))
sql("INSERT INTO skill_homunculus (homun_id,id,lv) VALUES (%d,8001,3)" % HOM)

def live_rows():
    return {
        "login": one("SELECT COUNT(*) FROM login WHERE account_id=%d" % OLD),
        "char": one("SELECT COUNT(*) FROM `char` WHERE char_id=%d" % C_OLD),
        "inv": one("SELECT COUNT(*) FROM inventory WHERE char_id=%d" % C_OLD),
        "stor": one("SELECT COUNT(*) FROM storage WHERE account_id=%d" % OLD),
        "pet": one("SELECT COUNT(*) FROM pet WHERE pet_id IN (%d,%d)" % (PET_EGG, PET_HATCHED)),
        "hom": one("SELECT COUNT(*) FROM homunculus WHERE homun_id=%d" % HOM),
        "reg": one("SELECT COUNT(*) FROM global_reg_value WHERE str LIKE 'ARCE2E%'"),
    }
try:
    srv("start"); time.sleep(3)
    busy = rostub.Session("arcbusy", "bspw1", log=lambda *a: None); busy.login(); busy.char_enter()  # stays at the select
    deadline = time.time() + 75
    while time.time() < deadline and one("SELECT COUNT(*) FROM arc_index WHERE state=1") != "2":
        time.sleep(3)
    try: busy.char_sock.close()
    except Exception: pass
    st = dict(sql("SELECT account_id, state FROM arc_index").split("\n") and [l.split("\t") for l in sql("SELECT account_id, state FROM arc_index").split("\n") if l])
    lr = live_rows()
    arc_ok = (one("SELECT COUNT(*) FROM arc_login WHERE account_id=%d" % OLD) == "1" and one("SELECT COUNT(*) FROM arc_char WHERE char_id=%d" % C_OLD) == "1"
              and one("SELECT COUNT(*) FROM arc_inventory WHERE char_id=%d" % C_OLD) == "3" and one("SELECT COUNT(*) FROM arc_storage WHERE account_id=%d" % OLD) == "2"
              and one("SELECT COUNT(*) FROM arc_pet WHERE char_id=%d" % C_OLD) == "2" and one("SELECT COUNT(*) FROM arc_homunculus WHERE homun_id=%d" % HOM) == "1"
              and one("SELECT COUNT(*) FROM arc_skill_homunculus WHERE homun_id=%d" % HOM) == "1" and one("SELECT COUNT(*) FROM arc_global_reg_value WHERE str LIKE 'ARCE2E%'") == "2"
              and one("SELECT COUNT(*) FROM arc_skill WHERE char_id=%d" % C_OLD) == "1")
    stays = one("SELECT COUNT(*) FROM login WHERE account_id IN (%d,%d,%d)" % (FRESH, NEWREG, BUSY))
    check("1 OLD + NEVER archived (state 1, rows in arc_*), gone live; FRESH, NEWREG, BUSY stay",
          st.get(str(OLD)) == "1" and st.get(str(NEVER)) == "1" and len(st) == 2 and arc_ok and set(lr.values()) == {"0"} and stays == "3"
          and one("SELECT COUNT(*) FROM login WHERE account_id=%d" % NEVER) == "0", "index=%s live=%s arc_ok=%s stays=%s" % (st, lr, arc_ok, stays))
    sp = sql("SELECT guild_id, partner_id FROM `char` WHERE char_id=%d" % C_FRESH)
    check("2 guild broken, spouse divorced (ring gone), friend row gone",
          one("SELECT COUNT(*) FROM guild WHERE guild_id=%d" % GUILD) == "0" and sp == "0\t0"
          and one("SELECT COUNT(*) FROM inventory WHERE char_id=%d AND nameid=2634" % C_FRESH) == "0"
          and one("SELECT COUNT(*) FROM friends WHERE char_id=%d" % C_FRESH) == "0",
          "guild=%s spouse=%s ring=%s friends=%s" % (one("SELECT COUNT(*) FROM guild WHERE guild_id=%d" % GUILD), sp,
           one("SELECT COUNT(*) FROM inventory WHERE char_id=%d AND nameid=2634" % C_FRESH), one("SELECT COUNT(*) FROM friends WHERE char_id=%d" % C_FRESH)))
    refused = ""
    try: rostub.Session("arcold", "wrongpw", log=lambda *a: None).login()
    except RuntimeError as e: refused = str(e)
    check("3 wrong password refused, archive untouched", "code=1" in refused and one("SELECT COUNT(*) FROM arc_login WHERE account_id=%d AND arc_new_aid=0" % OLD) == "1"
          and one("SELECT COUNT(*) FROM login WHERE userid='arcold'") == "0", refused)
    reg = ""
    try: rostub.Session("arcold_M", "newpw1", log=lambda *a: None).login()
    except RuntimeError as e: reg = str(e)
    fr = rostub.Session("arcfresh", "frpw1", log=lambda *a: None); fr.login(); fr.char_enter()
    mk = ""
    try: fr.make_char("ArcMaster", slot=2)
    except RuntimeError as e: mk = str(e)
    try: fr.char_sock.close()
    except Exception: pass
    check("4 registering the archived login refused; an archived char name refused",
          reg != "" and one("SELECT COUNT(*) FROM login WHERE userid='arcold'") == "0" and "refused" in mk, "reg=%r make=%r" % (reg, mk))
    time.sleep(1)
    s = rostub.Session("arcold", "oldpw1", log=lambda *a: None); s.login()
    _, res = s.char_enter()
    chars = res[1] if res[0] == "list" else []
    new_aid = s.aid
    new_cid = int(one("SELECT char_id FROM `char` WHERE name='ArcMaster'") or 0)
    check("5 logged in with a new account id, ArcMaster listed with a new char id",
          new_aid not in (0, OLD) and len(chars) == 1 and chars[0][1] == new_cid and new_cid not in (0, C_OLD), "aid=%s chars=%s cid=%s" % (new_aid, chars, new_cid))
    try: s.char_sock.close()
    except Exception: pass
    time.sleep(1)
    row = sql("SELECT account_id, guild_id, party_id, partner_id, pet_id, homun_id FROM `char` WHERE char_id=%d" % new_cid).split("\t")
    nh = int(row[5]) if len(row) == 6 else 0
    np_ = int(row[4]) if len(row) == 6 else 0
    egg_pet = int(one("SELECT pet_id FROM pet WHERE char_id=%d AND incuvate=1" % new_cid) or 0)
    n2, n3 = lohi(new_cid); q1, q2 = lohi(egg_pet)
    forged = one("SELECT COUNT(*) FROM inventory WHERE char_id=%d AND nameid=1201 AND card0=255 AND card2=%d AND card3=%d" % (new_cid, n2, n3))
    egg = one("SELECT COUNT(*) FROM inventory WHERE char_id=%d AND nameid=9001 AND card0=-256 AND card1=%d AND card2=%d" % (new_cid, q1, q2))
    stor = one("SELECT COUNT(*) FROM storage WHERE account_id=%d" % new_aid)
    stor_forged = one("SELECT COUNT(*) FROM storage WHERE account_id=%d AND card0=255 AND card2=%d AND card3=%d" % (new_aid, n2, n3))
    regs = sql("SELECT str, value, char_id, account_id FROM global_reg_value WHERE str LIKE 'ARCE2E%%' ORDER BY str")
    detail = dict(row=row, forged=forged, egg=egg, egg_pet=egg_pet, stor=stor, stor_forged=stor_forged, regs=regs,
                  skill=one("SELECT lv FROM skill WHERE char_id=%d AND id=228" % new_cid),
                  hom=one("SELECT name FROM homunculus WHERE homun_id=%d AND char_id=%d" % (nh, new_cid)),
                  homsk=one("SELECT lv FROM skill_homunculus WHERE homun_id=%d AND id=8001" % nh),
                  hatched=one("SELECT name FROM pet WHERE pet_id=%d AND char_id=%d" % (np_, new_cid)),
                  arc_left=one("SELECT COUNT(*) FROM arc_char") + "/" + one("SELECT COUNT(*) FROM arc_inventory") + "/" + one("SELECT COUNT(*) FROM arc_login WHERE userid='arcold'"),
                  state=one("SELECT state FROM arc_index WHERE account_id=%d" % OLD))
    check("6 restored: no guild/party/spouse; items, skill, vars, storage, pet + homunculus (new ids), maker/egg ids rewritten, arc rows gone",
          len(row) == 6 and int(row[0]) == new_aid and row[1:4] == ["0", "0", "0"] and forged == "1" and egg == "1" and egg_pet not in (0, PET_EGG)
          and np_ not in (0, PET_HATCHED) and nh not in (0, HOM) and stor == "2" and stor_forged == "1"
          and regs == "ARCE2E_ACC\t11\t0\t%d\nARCE2E_CHR\t22\t%d\t%d" % (new_aid, new_cid, new_aid)
          and detail["skill"] == "10" and detail["hom"] == "ArcHom" and detail["homsk"] == "3" and detail["hatched"] == "ArcPetOut"
          and detail["arc_left"] == "0/0/0" and detail["state"] == "2", str(detail))
finally:
    srv("stop")
    print(subprocess.run("sed 's/\\x1b\\[[0-9;]*m//g' %s/char.out %s/login.out | grep -a 'ARCHIVE\\|archived' | tail -12" % (run, run),
                         shell=True, stdout=subprocess.PIPE, text=True).stdout)
    cleanup()
    sql("ALTER TABLE login AUTO_INCREMENT=1; ALTER TABLE `char` AUTO_INCREMENT=1")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)

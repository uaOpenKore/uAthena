#!/usr/bin/env python3
"""e2e (SQL): a DB error while loading a character's pet / mercenary / guild / party / quest log /
achievements must not make the map-server drop them (the next save then wipes them).

Each scenario hides one table (RENAME) while the character logs in, puts it back, lets the character
play on and log out, and checks what the logout save left in the DB:
  pet         - char.pet_id stays (the old char-server said "not your pet": the map-server cleared it)
  merc        - mercenary_owner.merc_id stays ("no mercenary": the contract was dropped)
  guild       - char.guild_id stays ("no such guild": the map-server took the character out of it)
  party       - char.party_id stays (same for the party)
  quest       - the 5 stored quests stay although a new quest is taken (an empty log was sent: its save
                deleted the stored quests)
  questok     - the normal path: the log loads, a new quest is taken and saved with the stored ones
  achievement - the 3 stored achievements stay (an empty log was sent, the level achievements were
                completed again and the save deleted the others)

Usage: python3 -I loaderr2_e2e.py <run dir> <scenario>
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
from e2elib import Stream, enter_map, load_lengths, whisper  # noqa: E402

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
results = []
TABLE = {"pet": "pet", "merc": "mercenary", "guild": "guild", "party": "party", "quest": "quest",
         "achievement": "achievement", "questok": None}


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="latin-1").stdout.strip()


def check(name, cond, detail=""):
    results.append(cond)
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""),
          flush=True)


def count_log(run, text):
    return open(os.path.join(run, "char.out"), encoding="latin-1").read().count(text)


def main():
    run, scen = sys.argv[1], sys.argv[2]
    lengths = load_lengths()
    user, pw, name = ("user5", "heavypw", "Char5") if scen in ("pet", "merc") else ("sqlinj1", "injpw1", "SqlInj1")
    cid = int(sql("SELECT char_id FROM `char` WHERE name='%s'" % name))
    acc = int(sql("SELECT account_id FROM `char` WHERE char_id=%d" % cid))

    if scen == "pet":
        sql("DELETE FROM pet WHERE pet_id=80000")
        sql("INSERT INTO pet (pet_id, class, name, account_id, char_id, level, egg_id, equip, intimate, hungry, rename_flag, "
            "incuvate) VALUES (80000, 1002, 'Poring', %d, %d, 1, 9001, 0, 250, 50, 0, 0)" % (acc, cid))
        sql("UPDATE `char` SET pet_id=80000 WHERE char_id=%d" % cid)
    elif scen == "merc":
        sql("DELETE FROM mercenary WHERE mer_id=81000")
        sql("INSERT INTO mercenary (mer_id, char_id, class, hp, sp, kill_counter, life_time) VALUES "
            "(81000, %d, 6017, 1000, 100, 0, 3600000)" % cid)
        sql("REPLACE INTO mercenary_owner (char_id, merc_id, arch_calls, arch_faith, spear_calls, spear_faith, "
            "sword_calls, sword_faith) VALUES (%d, 81000, 0, 0, 0, 0, 0, 0)" % cid)
    elif scen == "guild":
        for t in ("guild", "guild_member", "guild_position"):
            sql("DELETE FROM %s WHERE guild_id=995" % t)
        sql("INSERT INTO guild (guild_id, name, char_id, master, guild_lv, connect_member, max_member, average_lv, exp, "
            "next_exp, skill_point, mes1, mes2, emblem_len, emblem_id) VALUES (995, 'LoadErrGuild', 150004, 'Char4', 1, 0, "
            "16, 10, 0, 100, 0, '', '', 0, 0)")
        sql("INSERT INTO guild_member (guild_id, account_id, char_id, hair, hair_color, gender, class, lv, exp, exp_payper, "
            "online, position, rsv1, rsv2, name) VALUES (995, 2000004, 150004, 1, 1, 0, 1, 10, 0, 0, 0, 0, 0, 0, 'Char4'), "
            "(995, %d, %d, 1, 1, 0, 1, 10, 0, 0, 0, 1, 0, 0, '%s')" % (acc, cid, name))
        sql("INSERT INTO guild_position (guild_id, position, name, mode, exp_mode) VALUES (995, 0, 'GM', 17, 0), "
            "(995, 1, 'Member', 0, 0)")
        sql("UPDATE `char` SET guild_id=995 WHERE char_id IN (150004, %d)" % cid)
    elif scen == "party":
        sql("UPDATE `char` SET party_id=1999 WHERE char_id=%d" % cid)
    elif scen in ("quest", "questok"):
        sql("DELETE FROM quest WHERE char_id=%d" % cid)
        sql("INSERT INTO quest (char_id, quest_id, state, time, count1, count2, count3) VALUES " +
            ", ".join("(%d, %d, '1', 0, 0, 0, 0)" % (cid, q) for q in range(1000, 1005)))
    elif scen == "achievement":
        sql("DELETE FROM achievement WHERE char_id=%d" % cid)
        sql("INSERT INTO achievement (char_id, achievement_id, count, completed, rewarded) VALUES "
            "(%d, 1, 50, 0, 0), (%d, 2, 30, 0, 0), (%d, 3, 500, 0, 0)" % (cid, cid, cid))
        sql("UPDATE `char` SET base_level=35 WHERE char_id=%d" % cid)  # level achievements (10, 11) complete at login

    table = TABLE[scen]
    if table:
        sql("RENAME TABLE `%s` TO `%s_e2e_hidden`" % (table, table))
    try:
        s = enter_map(user, pw, name)
        st = Stream(s.map_sock, lengths)
        st.collect(4)  # the map-server's load requests run (and fail) now
    finally:
        if table:
            sql("RENAME TABLE `%s_e2e_hidden` TO `%s`" % (table, table))
    if scen in ("quest", "questok"):
        whisper(s.map_sock, "npc:AuditVar", "setquest#1005")
        st.collect(2)
    st.collect(2)
    tag = "Saved char %d - %s" % (cid, name)
    n0 = count_log(run, tag)
    s.quit_game(wait=2)
    end = time.time() + 30
    while time.time() < end and count_log(run, tag) <= n0:
        time.sleep(1)
    time.sleep(2)

    if scen == "pet":
        v = sql("SELECT pet_id FROM `char` WHERE char_id=%d" % cid)
        check("the character keeps its pet (pet_id 80000)", v == "80000", v)
        sql("UPDATE `char` SET pet_id=0 WHERE char_id=%d" % cid)
        sql("DELETE FROM pet WHERE pet_id=80000")
    elif scen == "merc":
        v = sql("SELECT merc_id FROM mercenary_owner WHERE char_id=%d" % cid)
        check("the character keeps its mercenary contract (merc_id 81000)", v == "81000", v)
        sql("UPDATE mercenary_owner SET merc_id=0 WHERE char_id=%d" % cid)
        sql("DELETE FROM mercenary WHERE mer_id=81000")
    elif scen == "guild":
        v = sql("SELECT guild_id FROM `char` WHERE char_id=%d" % cid)
        check("the character stays in its guild (guild_id 995)", v == "995", v)
        for t in ("guild", "guild_member", "guild_position"):
            sql("DELETE FROM %s WHERE guild_id=995" % t)
        sql("UPDATE `char` SET guild_id=0 WHERE char_id IN (150004, %d)" % cid)
    elif scen == "party":
        v = sql("SELECT party_id FROM `char` WHERE char_id=%d" % cid)
        check("the character stays in its party (party_id 1999)", v == "1999", v)
        sql("UPDATE `char` SET party_id=0 WHERE char_id=%d" % cid)
    elif scen == "quest":
        v = sql("SELECT COUNT(*) FROM quest WHERE char_id=%d AND quest_id BETWEEN 1000 AND 1004" % cid)
        check("the 5 stored quests stay", v == "5", v)
    elif scen == "questok":
        v = sql("SELECT COUNT(*) FROM quest WHERE char_id=%d AND quest_id BETWEEN 1000 AND 1005" % cid)
        check("with the log loaded normally, the new quest is saved next to the 5 stored ones", v == "6", v)
    elif scen == "achievement":
        v = sql("SELECT COUNT(*) FROM achievement WHERE char_id=%d AND achievement_id IN (1, 2, 3)" % cid)
        check("the 3 stored achievements stay", v == "3", v)
        sql("UPDATE `char` SET base_level=1 WHERE char_id=%d" % cid)

    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

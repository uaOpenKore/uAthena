#!/usr/bin/env python3
"""e2e (SQL): small data-loss fixes.

Scenarios:
  mute    - a mute longer than 127 minutes must not stop the character's "seldom changed" row (class, hair,
            family, manner) from saving: `manner` is a TINYINT and STRICT_TRANS_TABLES rejected the UPDATE.
            SqlInj2 (GM) mutes itself for 200 minutes and changes its hair style, then logs out.
  delguild- deleting a character must break only the guild it is the master of (by char_id), not a guild
            whose stored master name merely equals the character's name.
  petegg  - deleting a character must delete the pets of its own eggs only: the egg's pet_id is
            card1 | card2 << 16 (it was computed as card1 | card2 << 2).
  rental  - saving an inventory with a permanent and a rental stack of the same item must keep each
            stack's expire_time with its own amount.

Usage: python3 -I smallfix_e2e.py <run dir> <scenario>
"""
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths  # noqa: E402

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
results = []


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="latin-1").stdout.strip()


def check(name, cond, detail=""):
    results.append(cond)
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""),
          flush=True)


def fake_map(port=16121):
    """Log in to the char-server as a map-server would (s1/p1); returns the socket."""
    m = socket.create_connection(("127.0.0.1", port), timeout=10)
    m.sendall(struct.pack("<H", 0x2AF8) + b"s1".ljust(24, b"\0") + b"p1".ljust(24, b"\0")
              + struct.pack("<I", 0) + socket.inet_aton("127.0.0.1") + struct.pack(">H", 15999))
    cmd, res = struct.unpack("<HB", rostub._recv_exact(m, 3, time.time() + 10))
    assert cmd == 0x2AF9 and res == 0, (cmd, res)
    return m


def delete_char(user, pw, cid, email="a@a.com"):
    s = rostub.Session(user, pw)
    s.login()
    s.char_enter()
    s.char_sock.sendall(struct.pack("<HI", 0x68, cid) + rostub._fixed(email, 40))
    reply = struct.unpack("<H", rostub._recv_exact(s.char_sock, 2, time.time() + 10))[0]
    s.char_sock.close()
    return reply


def new_char(user, pw, name, slot):
    s = rostub.Session(user, pw)
    s.login()
    _, res = s.char_enter()
    for sl, cid in res[1]:
        if sl == slot:
            s.char_sock.close()
            return cid
    cid = s.make_char(name, slot=slot)
    s.char_sock.close()
    return cid


def main():
    run, scen = sys.argv[1], sys.argv[2]
    lengths = load_lengths()

    if scen == "mute":
        sql("UPDATE `char` SET hair=1, manner=0 WHERE name='SqlInj2'")
        sql("DELETE FROM sc_data WHERE char_id=(SELECT char_id FROM `char` WHERE name='SqlInj2')")  # an earlier mute
        s = enter_map("sqlinj2", "injpw2", "SqlInj2")
        st = Stream(s.map_sock, lengths)
        st.collect(2)
        chat(s.map_sock, "SqlInj2", "@hairstyle 7")
        st.collect(1)
        chat(s.map_sock, "SqlInj2", "@mute 200 SqlInj2")
        st.collect(2)
        import os
        out = os.path.join(run, "char.out")
        tag = "Saved char %d - SqlInj2" % s.cid
        n0 = open(out, encoding="latin-1").read().count(tag)
        s.quit_game(wait=2)
        end = time.time() + 30  # wait for the logout save to reach the DB
        while time.time() < end and open(out, encoding="latin-1").read().count(tag) <= n0:
            time.sleep(1)
        time.sleep(1)
        row = sql("SELECT hair, manner FROM `char` WHERE name='SqlInj2'").split("\t")
        check("the hair style change is saved despite a 200-minute mute", row[0] == "7", row)
        check("the mute is saved (clamped to the column)", len(row) > 1 and int(row[1]) < 0, row)
        sql("UPDATE `char` SET manner=0 WHERE name='SqlInj2'")
        sql("DELETE FROM sc_data WHERE char_id=(SELECT char_id FROM `char` WHERE name='SqlInj2')")

    elif scen == "changegm":
        # guild 998: master Char3; members "Alexander" (150013) and "Alex" (150023), loaded in that order
        for t in ("guild", "guild_member", "guild_position"):
            sql("DELETE FROM %s WHERE guild_id=998" % t)
        sql("UPDATE `char` SET name='Alexander', guild_id=998 WHERE char_id=150013")
        sql("UPDATE `char` SET name='Alex', guild_id=998 WHERE char_id=150023")
        sql("UPDATE `char` SET guild_id=998 WHERE char_id=150003")
        sql("INSERT INTO guild (guild_id, name, char_id, master, guild_lv, connect_member, max_member, average_lv, exp, "
            "next_exp, skill_point, mes1, mes2, emblem_len, emblem_id) VALUES (998, 'PrefixTest', 150003, 'Char3', 1, 0, 16, 10, "
            "0, 100, 0, '', '', 0, 0)")
        for cid, acc, pos, name in ((150003, 2000003, 0, "Char3"), (150013, 2000013, 1, "Alexander"),
                                    (150023, 2000023, 1, "Alex")):
            sql("INSERT INTO guild_member (guild_id, account_id, char_id, hair, hair_color, gender, class, lv, exp, "
                "exp_payper, online, position, rsv1, rsv2, name) VALUES (998, %d, %d, 1, 1, 0, 1, 10, 0, 0, 0, %d, 0, 0, '%s')"
                % (acc, cid, pos, name))
        m = fake_map()
        m.sendall(struct.pack("<HHI", 0x3033, 4 + 8, 998) + b"Alex")
        time.sleep(2)
        m.close()
        subprocess.run(["/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/sqlaudit/srv.sh",
                        "stop", run], stdout=subprocess.DEVNULL)  # the final save writes the guild
        row = sql("SELECT master, char_id FROM guild WHERE guild_id=998").split("\t")
        check("@changegm to 'Alex' makes Alex master, not 'Alexander'", row == ["Alex", "150023"], row)

    elif scen == "delguild":
        sql("UPDATE login SET email='a@a.com' WHERE userid='sqlinj1'")
        cid = new_char("sqlinj1", "injpw1", "DelGuildVic", 1)
        for t in ("guild", "guild_member", "guild_position", "guild_storage"):
            sql("DELETE FROM %s WHERE guild_id IN (996, 997)" % t)
        sql("INSERT INTO guild (guild_id, name, char_id, master, guild_lv, connect_member, max_member, average_lv, exp, "
            "next_exp, skill_point, mes1, mes2, emblem_len, emblem_id) VALUES "
            "(997, 'OwnGuild', 150004, 'Char4', 1, 0, 16, 10, 0, 100, 0, '', '', 0, 0), "
            "(996, 'StaleGuild', 150006, 'DelGuildVic', 1, 0, 16, 10, 0, 100, 0, '', '', 0, 0)")
        acc = sql("SELECT account_id FROM login WHERE userid='sqlinj1'")
        sql("INSERT INTO guild_member (guild_id, account_id, char_id, hair, hair_color, gender, class, lv, exp, exp_payper, "
            "online, position, rsv1, rsv2, name) VALUES (997, 2000004, 150004, 1, 1, 0, 1, 10, 0, 0, 0, 0, 0, 0, 'Char4'), "
            "(997, %s, %d, 1, 1, 0, 1, 10, 0, 0, 0, 1, 0, 0, 'DelGuildVic')" % (acc, cid))
        sql("UPDATE `char` SET guild_id=997 WHERE char_id IN (150004, %d)" % cid)
        sql("INSERT INTO guild_storage (guild_id, nameid, amount, equip, identify, refine, attribute, card0, card1, card2, "
            "card3, expire_time) SELECT 997, 501 + seq, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0 FROM seq_0_to_9")
        reply = delete_char("sqlinj1", "injpw1", cid)
        time.sleep(2)
        check("the character is deleted (0x6f)", reply == 0x6F, "0x%04x" % reply)
        check("its own guild survives (the character was not its master)",
              sql("SELECT COUNT(*) FROM guild WHERE guild_id=997") == "1")
        check("that guild's storage is untouched", sql("SELECT COUNT(*) FROM guild_storage WHERE guild_id=997") == "10")

    elif scen == "petegg":
        sql("UPDATE login SET email='a@a.com' WHERE userid='sqlinj1'")
        acc = sql("SELECT account_id FROM login WHERE userid='sqlinj1'")
        cid = new_char("sqlinj1", "injpw1", "PetEggVic", 2)
        sql("INSERT IGNORE INTO pet (pet_id, class, name, account_id, char_id, level, egg_id, equip, intimate, hungry, "
            "rename_flag, incuvate) VALUES (4468, 1002, 'Poring', 2002335, 172335, 1, 9001, 0, 250, 50, 0, 1)")
        other = sql("SELECT char_id FROM pet WHERE pet_id=4468")
        sql("DELETE FROM pet WHERE pet_id=70000")
        sql("INSERT INTO pet (pet_id, class, name, account_id, char_id, level, egg_id, equip, intimate, hungry, "
            "rename_flag, incuvate) VALUES (70000, 1002, 'Poring', %s, %d, 1, 9001, 0, 250, 50, 0, 1)" % (acc, cid))
        sql("INSERT INTO inventory (char_id, nameid, amount, equip, identify, refine, attribute, card0, card1, card2, card3, "
            "expire_time) VALUES (%d, 9001, 1, 0, 1, 0, 0, -256, %d, %d, 0, 0)" % (cid, 70000 & 0xFFFF, 70000 >> 16))
        reply = delete_char("sqlinj1", "injpw1", cid)
        time.sleep(2)
        check("the character is deleted (0x6f)", reply == 0x6F, "0x%04x" % reply)
        check("another player's pet 4468 (owner %s) is untouched" % other, sql("SELECT COUNT(*) FROM pet WHERE pet_id=4468") == "1")
        check("the deleted character's egg pet 70000 is deleted", sql("SELECT COUNT(*) FROM pet WHERE pet_id=70000") == "0")

    elif scen == "rental":
        exp = int(time.time()) + 7 * 86400
        sql("DELETE FROM inventory WHERE char_id=150005 AND nameid=607")
        sql("INSERT INTO inventory (char_id, nameid, amount, equip, identify, refine, attribute, card0, card1, card2, card3, "
            "expire_time) VALUES (150005, 607, 10, 0, 1, 0, 0, 0, 0, 0, 0, 0), (150005, 607, 5, 0, 1, 0, 0, 0, 0, 0, 0, %d)" % exp)
        a, b = sql("SELECT id FROM inventory WHERE char_id=150005 AND nameid=607 ORDER BY id").split()
        s = enter_map("user5", "heavypw", "Char5")
        st = Stream(s.map_sock, lengths)
        st.collect(3)
        # swap the two rows' ids: the save now reads them in the other order than the map-server holds them
        sql("UPDATE inventory SET id=id+100000000 WHERE id=%s" % a)
        sql("UPDATE inventory SET id=%s WHERE id=%s" % (a, b))
        sql("UPDATE inventory SET id=%s WHERE id=%d" % (b, int(a) + 100000000))
        chat(s.map_sock, "Char5", "@item 502 1")  # an inventory change, so the save compares every row
        st.collect(2)
        import os
        out = os.path.join(run, "char.out")
        n0 = open(out, encoding="latin-1").read().count("Saved char 150005 - Char5: inventory")
        s.quit_game(wait=2)
        end = time.time() + 30  # wait for the inventory save to reach the DB
        while time.time() < end and open(out, encoding="latin-1").read().count("Saved char 150005 - Char5: inventory") <= n0:
            time.sleep(1)
        time.sleep(1)
        perm = sql("SELECT SUM(amount) FROM inventory WHERE char_id=150005 AND nameid=607 AND expire_time=0")
        rent = sql("SELECT SUM(amount) FROM inventory WHERE char_id=150005 AND nameid=607 AND expire_time=%d" % exp)
        check("the permanent stack keeps its 10 (expire_time 0)", perm == "10", "perm=%s rental=%s" % (perm, rent))
        check("the rental stack keeps its 5", rent == "5", "perm=%s rental=%s" % (perm, rent))
        sql("DELETE FROM inventory WHERE char_id=150005 AND nameid=607")

    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""e2e (SQL): one save = one transaction, and a failed save is written again later.

A BEFORE INSERT trigger makes every INSERT into one table fail while DELETE still works - the dangerous
case of the "delete the rows, insert the new ones" saves.

Scenarios:
  charsave - Char5 gets +1000 zeny and new skills, logs out while skill INSERTs fail. The old char-server
             deleted the skills and kept the zeny (a half save, the skills lost for good). Now nothing of
             the save is stored, the character can't be loaded while the save still fails, and once the
             INSERTs work again the kept save is written by the retry timer (zeny and skills).
  storage  - Char5 moves its inventory into the storage while storage INSERTs fail. The old char-server
             lost the items (the inventory save removed them, the storage save failed); now the storage
             save is written once INSERTs work again: no item is lost.
  registry - SqlInj1 sets a char variable while variable INSERTs fail. The old char-server deleted all
             of the character's variables; now they stay, and the new one is written later.

Usage: python3 -I tx_e2e.py <run dir> <scenario>
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths, whisper  # noqa: E402

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
results = []


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="latin-1").stdout.strip()


def check(name, cond, detail=""):
    results.append(cond)
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""),
          flush=True)


def block_inserts(table):
    sql("DROP TRIGGER IF EXISTS e2e_block_insert")
    sql("CREATE TRIGGER e2e_block_insert BEFORE INSERT ON `%s` FOR EACH ROW "
        "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'e2e: inserts refused'" % table)


def allow_inserts():
    sql("DROP TRIGGER IF EXISTS e2e_block_insert")


def wait_log(run, text, n0, seconds=30):
    out = os.path.join(run, "char.out")
    end = time.time() + seconds
    while time.time() < end:
        if open(out, encoding="latin-1").read().count(text) > n0:
            return True
        time.sleep(1)
    return False


def count_log(run, text):
    return open(os.path.join(run, "char.out"), encoding="latin-1").read().count(text)


def main():
    run, scen = sys.argv[1], sys.argv[2]
    lengths = load_lengths()
    allow_inserts()

    if scen == "charsave":
        sql("DELETE FROM skill WHERE char_id=150005")
        sql("INSERT INTO skill (char_id, id, lv) VALUES (150005, 1, 9), (150005, 36, 1), (150005, 37, 1)")
        skills0 = sql("SELECT COUNT(*), COALESCE(SUM(lv),0) FROM skill WHERE char_id=150005")
        zeny0 = int(sql("SELECT zeny FROM `char` WHERE char_id=150005"))
        s = enter_map("user5", "heavypw", "Char5")
        st = Stream(s.map_sock, lengths)
        st.collect(2)
        chat(s.map_sock, "Char5", "@zeny 1000")
        st.collect(1)
        chat(s.map_sock, "Char5", "@skillall")
        st.collect(2)
        block_inserts("skill")
        try:
            n0 = count_log(run, "Saved char 150005") + count_log(run, "Saving char 150005 - Char5 failed")
            s.quit_game(wait=2)
            end = time.time() + 30  # the final save: logged either as saved or as rolled back
            while time.time() < end and count_log(run, "Saved char 150005") + \
                    count_log(run, "Saving char 150005 - Char5 failed") <= n0:
                time.sleep(1)
            time.sleep(1)
            skills1 = sql("SELECT COUNT(*), COALESCE(SUM(lv),0) FROM skill WHERE char_id=150005")
            zeny1 = int(sql("SELECT zeny FROM `char` WHERE char_id=150005"))
            check("a save whose skill INSERT fails stores nothing: skills unchanged", skills1 == skills0,
                  "%s -> %s" % (skills0, skills1))
            check("... and zeny unchanged", zeny1 == zeny0, "%d -> %d" % (zeny0, zeny1))
            # while the save still fails, the character must not be loaded (it would be played with old data)
            o = rostub.Session("user5", "heavypw")
            o.login()
            o.char_enter()
            loaded = True
            try:
                o.select_char(0, timeout=6)
            except Exception:  # noqa: BLE001
                loaded = False
            check("the character is not loaded while its save still fails", not loaded)
            try:
                o.char_sock.close()
            except Exception:  # noqa: BLE001
                pass
        finally:
            allow_inserts()
        wrote = wait_log(run, "the failed save of char 150005 - Char5 is written now", 0, 20)
        skills2 = sql("SELECT COUNT(*), COALESCE(SUM(lv),0) FROM skill WHERE char_id=150005")
        zeny2 = int(sql("SELECT zeny FROM `char` WHERE char_id=150005"))
        check("once INSERTs work, the kept save is written (retry timer)", wrote)
        check("... with the new zeny", zeny2 == zeny0 + 1000, "%d -> %d" % (zeny0, zeny2))
        check("... and the new skills", skills2 != skills0 and int(skills2.split()[0]) > 0, "%s -> %s" % (skills0, skills2))
        s2 = rostub.Session("user5", "heavypw")
        s2.login()
        s2.char_enter()
        ok = True
        try:
            s2.select_char(0, timeout=10)
        except Exception:  # noqa: BLE001
            ok = False
        check("then the character loads again", ok)
        try:
            s2.char_sock.close()
        except Exception:  # noqa: BLE001
            pass

    elif scen == "storage":
        nid = 607
        sql("DELETE FROM inventory WHERE char_id=150005 AND nameid=%d" % nid)
        sql("DELETE FROM storage WHERE account_id=2000005 AND nameid=%d" % nid)
        sql("INSERT INTO inventory (char_id, nameid, amount, equip, identify, refine, attribute, card0, card1, card2, "
            "card3, expire_time) VALUES (150005, %d, 7, 0, 1, 0, 0, 0, 0, 0, 0, 0)" % nid)
        s = enter_map("user5", "heavypw", "Char5")
        st = Stream(s.map_sock, lengths)
        st.collect(2)
        chat(s.map_sock, "Char5", "@storage")
        st.collect(3)
        block_inserts("storage")
        try:
            n0 = count_log(run, "storage_tosql: saving the storage of account 2000005 failed")
            chat(s.map_sock, "Char5", "@storeall")
            st.collect(3)
            s.map_sock.sendall(b"\xf7\x00")  # close the storage: the storage save
            st.collect(3)
            s.quit_game(wait=4)
            time.sleep(3)
            rolled = count_log(run, "storage_tosql: saving the storage of account 2000005 failed") > n0
            w0 = count_log(run, "the failed save of account storage 2000005 is written now")
        finally:
            allow_inserts()
        # count from before the allow: char.out keeps the lines of earlier runs, a 0 here returned at once and the
        # storage was read before the 10 s retry timer wrote it (the test passed only on a lucky timer phase)
        wrote = wait_log(run, "the failed save of account storage 2000005 is written now", w0, 25)
        inv = sql("SELECT COALESCE(SUM(amount),0) FROM inventory WHERE char_id=150005 AND nameid=%d" % nid)
        sto = sql("SELECT COALESCE(SUM(amount),0) FROM storage WHERE account_id=2000005 AND nameid=%d" % nid)
        check("the storage save failed while INSERTs were refused (rolled back)", rolled or sto == "7",
              "rolled=%s" % rolled)
        check("the 7 items are not lost (inventory %s + storage %s)" % (inv, sto), int(inv) + int(sto) == 7)
        check("they are in the storage", sto == "7", "storage=%s" % sto)
        del wrote

    elif scen == "registry":
        cid = sql("SELECT char_id FROM `char` WHERE name='SqlInj1'")
        sql("DELETE FROM global_reg_value WHERE type=3 AND char_id=%s" % cid)
        for i in range(10):
            sql("INSERT INTO global_reg_value (char_id, str, value, type, account_id) VALUES (%s, 'TXVAR%02d', '%d', 3, 0)"
                % (cid, i, i))
        s = enter_map("sqlinj1", "injpw1", "SqlInj1")
        st = Stream(s.map_sock, lengths)
        st.collect(2)
        block_inserts("global_reg_value")
        val = int(time.time()) % 1000 + 1
        try:
            n0 = count_log(run, "e2e: inserts refused")
            whisper(s.map_sock, "npc:AuditVar", "setchar#%d" % val)
            st.collect(3)
            s.quit_game(wait=2)
            hit = wait_log(run, "e2e: inserts refused", n0, 40)  # keep INSERTs refused until the save tried one
            check("the variable save ran while INSERTs were refused", hit)
            time.sleep(1)
            kept = sql("SELECT COUNT(*) FROM global_reg_value WHERE type=3 AND char_id=%s AND str LIKE 'TXVAR%%'" % cid)
            check("a variable save whose INSERT fails deletes nothing", kept == "10", kept)
        finally:
            allow_inserts()
        end = time.time() + 20
        while time.time() < end and sql("SELECT value FROM global_reg_value WHERE type=3 AND char_id=%s AND "
                                        "str='AUDIT_CHARVAR'" % cid) != str(val):
            time.sleep(1)
        kept = sql("SELECT COUNT(*) FROM global_reg_value WHERE type=3 AND char_id=%s AND str LIKE 'TXVAR%%'" % cid)
        newv = sql("SELECT value FROM global_reg_value WHERE type=3 AND char_id=%s AND str='AUDIT_CHARVAR'" % cid)
        check("once INSERTs work, the save is written: the 10 old variables", kept == "10", kept)
        check("... and the new one", newv == str(val), newv)

    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

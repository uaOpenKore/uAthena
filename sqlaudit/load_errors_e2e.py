#!/usr/bin/env python3
"""e2e (SQL): a failed DB read must never be handed to the map-server as empty data, because the next save
of that empty data deletes what is stored. Also the char-server must not hang on a failed read.

Scenarios (one per run; the stand must be up, except where noted):
  charload  - the `skill` table can't be read while Char5 is selected; after it is back and an autosave ran,
              Char5 must still have all its skills (the old char-server sent the character with no skills
              and the save replaced them with level-0 rows)
  scdata    - `sc_data` can't be read while a character enters the map: the char-server must keep answering
              (it used to re-run the failing query forever)
  storage   - `storage` can't be read when Char5 opens it; after it is back, @storeall + close must not
              delete the stored items (the old char-server opened an empty storage)
  registry  - the char-server's DB user can't read global_reg_value values (run with char_server_id
              charaudit, see the runner); a char variable set afterwards must not wipe the stored ones
  reglong   - a character with more than 5000 bytes of variables must get all of them, so that saving
              one change keeps every variable (the reply used to stop at 5000 bytes)

Usage: python3 -I load_errors_e2e.py <run dir> <scenario>
  accounts: user5/heavypw (GM 99, Char5 cid 150005, account 2000005), sqlinj1 (SqlInj1).
"""
import os
import struct
import subprocess
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import Stream, chat, enter_map, load_lengths, messages, whisper  # noqa: E402

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
results = []


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="latin-1").stdout.strip()


def check(name, cond, detail=""):
    results.append(cond)
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""),
          flush=True)


def try_enter(user, pw, timeout=12):
    """Login + char select slot 0 + map enter; returns the session or None if the char-server never answered."""
    s = rostub.Session(user, pw)
    s.login()
    s.char_enter()
    try:
        s.select_char(0, timeout=timeout)
    except Exception:  # noqa: BLE001
        return None
    res = s.map_enter()
    return s if res[0] == "ok" else None


def main():
    run, scen = sys.argv[1], sys.argv[2]
    lengths = load_lengths()

    if scen == "charload":
        before = sql("SELECT COUNT(*), SUM(lv) FROM skill WHERE char_id=150005")
        sql("RENAME TABLE skill TO skill_e2e_hidden")
        try:
            s = try_enter("user5", "heavypw")
        finally:
            sql("RENAME TABLE skill_e2e_hidden TO skill")
        if s:
            Stream(s.map_sock, lengths).collect(25)  # an autosave (20 s in the run conf)
            s.quit_game(wait=3)
        after = sql("SELECT COUNT(*), SUM(lv) FROM skill WHERE char_id=150005")
        check("Char5 keeps every skill (rows, levels)", after == before, "%s -> %s" % (before, after))

    elif scen == "scdata":
        sql("RENAME TABLE sc_data TO sc_data_e2e_hidden")
        try:
            s = enter_map("sqlinj1", "injpw1", "SqlInj1")
            time.sleep(2)
            t0 = time.time()
            ok = True
            try:
                o = rostub.Session("user5", "heavypw")
                o.login()
                _, res = o.char_enter(timeout=8)
                ok = res[0] == "list"
            except Exception as e:  # noqa: BLE001
                ok, res = False, str(e)
            check("the char-server still answers while the sc_data read fails", ok and time.time() - t0 < 5,
                  "%.1f s, %s" % (time.time() - t0, res))
        finally:
            sql("RENAME TABLE sc_data_e2e_hidden TO sc_data")
        try:
            s.kill_map()
        except Exception:  # noqa: BLE001
            pass

    elif scen == "storage":
        before = sql("SELECT COUNT(*), SUM(amount) FROM storage WHERE account_id=2000005")
        s = enter_map("user5", "heavypw", "Char5")
        st = Stream(s.map_sock, lengths)
        st.collect(2)
        chat(s.map_sock, "Char5", "@item 501 5")
        st.collect(1)
        sql("RENAME TABLE storage TO storage_e2e_hidden")
        try:
            chat(s.map_sock, "Char5", "@storage")
            st.collect(3)
        finally:
            sql("RENAME TABLE storage_e2e_hidden TO storage")
        chat(s.map_sock, "Char5", "@storeall")
        st.collect(3)
        s.map_sock.sendall(struct.pack("<H", 0xF7))  # close the storage
        st.collect(3)
        s.quit_game(wait=3)
        after = sql("SELECT COUNT(*) FROM storage WHERE account_id=2000005")
        check("the stored items are still there (rows)", int(after) >= int(before.split()[0]),
              "%s -> %s" % (before, after))

    elif scen in ("registry", "reglong"):
        # SqlInj1 gets N stored char variables (reglong: 40 of 150 bytes, over 5000 bytes in all); then one more
        # variable is set in game, the character logs out (save), and all N must still be stored.
        cid = sql("SELECT char_id FROM `char` WHERE name='SqlInj1'")
        n, size = (40, 50) if scen == "reglong" else (10, 1)
        sql("DELETE FROM global_reg_value WHERE type=3 AND char_id=%s" % cid)
        for i in range(n):
            sql("INSERT INTO global_reg_value (char_id, str, value, type, account_id) VALUES (%s, 'KEEPVAR%02d', "
                "'%s', 3, 0)" % (cid, i, ("v%02d" % i) * size))
        s = enter_map("sqlinj1", "injpw1", "SqlInj1")
        st = Stream(s.map_sock, lengths)
        st.collect(2)
        val = int(time.time()) % 1000 + 1
        whisper(s.map_sock, "npc:AuditVar", "setchar#%d" % val)
        st.collect(3)
        s.quit_game(wait=2)
        end = time.time() + 25  # wait for the char variable save to land (it may never come: then nothing saved)
        while time.time() < end and sql("SELECT value FROM global_reg_value WHERE type=3 AND char_id=%s AND "
                                        "str='AUDIT_CHARVAR'" % cid) != str(val):
            time.sleep(1)
        time.sleep(2)
        kept = sql("SELECT COUNT(*) FROM global_reg_value WHERE type=3 AND char_id=%s AND str LIKE 'KEEPVAR%%'" % cid)
        check("all %d stored char variables survive the save (%s)" % (n, scen), kept == str(n), kept)

    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

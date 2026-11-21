#!/usr/bin/env python3
"""e2e (SQL): login-server SQL hardening.

 1. New account (<name>_M) with a quote in the name and the password: created as typed, then logs in.
 2. A new-account name that carries SQL (x'OR SLEEP(..)OR'_M) must not run it: the login-server answers at once.
 3. @email (GM level 1) with a quote in the new address must store the address, not run SQL
    (z@a.b',level='99 used to set the account's GM level to 99).
 4. 0x272e (##account vars on map entry) with the table unreadable: the login-server keeps answering logins
    (it used to re-run the failing query forever).
 5. 0x2727 (@changesex) for an account without a login row: the char-server link keeps working
    (the packet stayed unread and blocked every later packet from that char-server).

Usage: python3 -I login_sql_e2e.py <run dir>
  Stand from mkrun.sh/srv.sh with allowed_regs raised; before boot the audit DB has sqlinj1 (GM 1) and
  sqlinj2 (GM 99), see login_sql_e2e_setup.sql.
"""
import subprocess
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
import rostub  # noqa: E402
from e2elib import chat, enter_map  # noqa: E402

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-B", "-e"]
results = []


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          encoding="latin-1").stdout.strip()


def check(name, cond, detail=""):
    results.append(cond)
    print("%s  %s%s" % ("ok  " if cond else "FAIL", name, ("  [%s]" % detail) if detail and not cond else ""),
          flush=True)


def try_login(user, pw, timeout=10):
    t0 = time.time()
    try:
        rostub.Session(user, pw).login(timeout=timeout)
        return "ok", time.time() - t0
    except Exception as e:  # noqa: BLE001
        return str(e), time.time() - t0


def main():
    # 1. quote in a new account's name and password
    res, _ = try_login("qa'b_M", "pw'x1")
    check("new account qa'b (quote in name and password) is accepted", res == "ok", res)
    stored = sql("SELECT user_pass FROM login WHERE userid='qa\\'b'")
    check("it is stored under its own name with the password as typed", stored == "pw'x1", repr(stored))
    res, _ = try_login("qa'b", "pw'x1")
    check("qa'b logs in with pw'x1", res == "ok", res)

    # 2. SQL in a new account's name
    res, dt = try_login("x'OR SLEEP(0.0005)OR'_M", "pwpw1", timeout=30)
    check("SQL in a new account name is not run (answer in < 1 s)", dt < 1.0, "%.1f s, %s" % (dt, res))

    # 3. @email with a quote in the new address
    s = enter_map("sqlinj1", "injpw1", "SqlInj1")
    time.sleep(1)
    chat(s.map_sock, "SqlInj1", "@email a@a.com z@a.b',level='99")
    time.sleep(3)
    row = sql("SELECT level, email FROM login WHERE userid='sqlinj1'").split("\t")
    check("@email does not change the GM level", row[0] == "1", row)
    check("@email stores the new address as typed", len(row) > 1 and row[1] == "z@a.b',level='99", row)
    s.quit_game()

    # 4. 0x272e with global_reg_value unreadable (sqlinj2 gets its character first)
    s2 = enter_map("sqlinj2", "injpw2", "SqlInj2")
    time.sleep(1)
    s2.quit_game()
    time.sleep(3)
    sql("RENAME TABLE global_reg_value TO grv_e2e_hidden")
    try:
        s2 = rostub.Session("sqlinj2", "injpw2")
        s2.login()
        s2.char_enter()
        s2.select_char(0)
        s2.map_enter()          # map-server asks the login-server for ##vars -> 0x272e fails
        time.sleep(2)
        res, dt = try_login("user7", "wrongpw", timeout=8)
        check("login-server still answers while the ##var query fails", "0x6a" in res and dt < 3,
              "%.1f s, %s" % (dt, res))
    finally:
        sql("RENAME TABLE grv_e2e_hidden TO global_reg_value")
    try:
        s2.kill_map()
    except Exception:  # noqa: BLE001
        pass
    time.sleep(2)

    # 5. 0x2727 for an account without a login row
    s3 = enter_map("sqlinj2", "injpw2", "SqlInj2")
    time.sleep(1)
    sql("UPDATE login SET userid='sqlinj2_hidden', account_id=account_id+1000000 WHERE userid='sqlinj2'")
    try:
        chat(s3.map_sock, "SqlInj2", "@changesex")
        time.sleep(2)
        s4 = rostub.Session("user8", "heavypw8")
        sql("UPDATE login SET user_pass='heavypw8' WHERE userid='user8'")
        res = "?"
        try:
            s4.login()
            _, res = s4.char_enter(timeout=8)
        except Exception as e:  # noqa: BLE001
            res = str(e)
        check("char select still works after 0x2727 for a missing account", isinstance(res, tuple) and
              res[0] == "list", res)
    finally:
        sql("UPDATE login SET userid='sqlinj2', account_id=account_id-1000000 WHERE userid='sqlinj2_hidden'")

    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""e2e (SQL): @reloadscript must not roll a global ($) variable back to the value stored before the last flush.

mapreg writes go through the async writer (flushed every 20 s); script_reload queued the save and then read the
table back at once, so a global changed less than a flush ago came back with its old value. The test sets
$AUDIT_RELOAD to a new value through a test NPC, runs @reloadscript right away, then asks the NPC for the value.

Usage: python3 -I mapreg_reload_e2e.py <run dir>   (stand from mkrun.sh/srv.sh with e2e_npc/auditvar.txt loaded;
       account user5/heavypw has GM 99 in the audit DB)
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, "/tmp/claude-0/-root-uaroClient/f1b47459-6a36-42ec-9fb0-528e8a9c2531/scratchpad/c1/e2e")
from e2elib import Stream, chat, enter_map, load_lengths, messages, whisper  # noqa: E402

MYSQL = ["mysql", "--no-defaults", "-h127.0.0.1", "-P13306", "-uroot", "ragnarok", "-N", "-e"]


def sql(q):
    return subprocess.run(MYSQL + [q], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.strip()


def wait_msg(st, prefix, seconds):
    end = time.time() + seconds
    while time.time() < end:
        for m in messages(st.collect(0.5)):
            if m.startswith(prefix):
                return m
    return None


def main():
    run = sys.argv[1]
    lengths = load_lengths()
    s = enter_map("user5", "heavypw", "Char5")
    st = Stream(s.map_sock, lengths)
    st.collect(2)

    whisper(s.map_sock, "npc:AuditVar", "get")
    before = wait_msg(st, "auditvar get", 10)
    print("  before:", before)
    new_val = 111 if before != "auditvar get 111" else 222

    whisper(s.map_sock, "npc:AuditVar", "set#%d" % new_val)
    print("  set   :", wait_msg(st, "auditvar set", 10))

    t0 = time.time()
    chat(s.map_sock, "Char5", "@reloadscript")
    done = wait_msg(st, "Scripts reloaded", 120)
    print("  reload: %s (%.1f s)" % (done, time.time() - t0))
    st.collect(3)

    whisper(s.map_sock, "npc:AuditVar", "get")
    after = wait_msg(st, "auditvar get", 10)
    print("  after :", after)
    s.quit_game()
    time.sleep(25)  # past one async flush
    db = sql("SELECT value FROM mapreg WHERE varname='$AUDIT_RELOAD'")
    print("  DB    :", db.replace("\n", ","))

    ok = after == "auditvar get %d" % new_val
    print("%s  the global keeps the value set right before @reloadscript" % ("ok  " if ok else "FAIL"))
    ok_db = db == str(new_val)
    print("%s  the table holds the same value" % ("ok  " if ok_db else "FAIL"))
    print("ALL PASSED" if ok and ok_db else "FAILED")
    sys.exit(0 if ok and ok_db else 1)


if __name__ == "__main__":
    main()

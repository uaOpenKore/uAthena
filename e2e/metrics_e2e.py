#!/usr/bin/env python3
"""e2e drive for the [LOOPMETRIC]/[SAVEMETRIC]/[RELOGMETRIC]/[MOBMETRIC] lines (checked from the logs by
run_metrics.sh): a GM @reloadscript (a long main-loop round -> slow_loop), 15 quick character selects of V
(RELOGMETRIC), a map login + logout of A (SAVEMETRIC final save). Usage: python3 -I metrics_e2e.py <PacketTable.cpp>"""
import os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rostub  # noqa: E402
from elemark_e2e import USER, PW, Stream, load_lengths, chat  # noqa: E402

s = rostub.Session(USER, PW, log=lambda *a: None)
s.login(); _, res = s.char_enter(); s.select_char(res[1][0][0]); assert s.map_enter()[0] == "ok"
st = Stream(s.map_sock, load_lengths(sys.argv[1]))
st.drain(1.5)
chat(s.map_sock, "@reloadscript")
st.drain(8)
print("reloadscript sent", flush=True)
for i in range(11):
    v = rostub.Session("e2etestv", "e2epass1", log=lambda *a: None)
    v.login(); _, r = v.char_enter(); v.select_char(r[1][0][0])
print("11 selects of V done", flush=True)
s.quit_game(wait=1)
print("A logged out", flush=True)

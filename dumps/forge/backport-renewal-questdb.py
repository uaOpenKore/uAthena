#!/usr/bin/env python3
"""SP-2 2-pre: backport renewal quest_db rAthena -> uAthena db/quest_db.txt.

Quest-IDs used by IN renewal quest scripts (npc/re/quests minus OUT episodes) and missing
from uAthena quest_db.txt. Source: rAthena db/re/quest_db.yml. Output (9-field eAthena row):
  ID,Time,Target1,Val1,Target2,Val2,Target3,Val3,"Title"
yml Targets carry Mob AEGIS-names -> converted to mob-id via mob_db; up to 3 targets, extra
dropped+logged; a target whose mob is absent from uAthena mob_db -> id 0 (objective neutralised).
Modes: --selftest | --dry-run | (default) generate. Idempotent (rewrites GENERATED block).
"""
import os, re, sys, subprocess

UA = os.environ.get("UA_ROOT", ".")
RA = os.environ.get("RA_ROOT", "/tmp/rathena-ref")
GEN_HDR = "// ===== Backport renewal quest_db (GENERATED) ====="
GEN_END = "// ===== end renewal quest_db ====="
OUT_EPISODES = {"quests_14_3", "quests_14_3_bis", "quests_15_1", "quests_15_2",
                "quests_16_1", "quests_16_2", "quests_17_1", "quests_17_2", "quests_18"}

def rd(p):
    with open(p, encoding="latin-1") as f:
        return f.read()

def mob_aegis2id():
    m = {}
    for fn in ("db/mob_db.txt", "db/mob_db2.txt"):
        p = os.path.join(UA, fn)
        if not os.path.exists(p):
            continue
        for ln in rd(p).splitlines():
            if ln.lstrip().startswith("//"):
                continue
            c = ln.split(",")
            if len(c) >= 2 and c[0].strip().isdigit():
                m[c[1].strip().upper()] = c[0].strip()
    return m

def ua_quest_ids():
    ids = set()
    for ln in rd(os.path.join(UA, "db", "quest_db.txt")).splitlines():
        mm = re.match(r'\s*(\d+),', ln)
        if mm and not ln.lstrip().startswith("//"):
            ids.add(int(mm.group(1)))
    return ids

def ra_show(rel):
    return subprocess.run(["git", "-C", RA, "show", f"HEAD:{rel}"],
                          capture_output=True).stdout.decode("latin-1")

def used_quest_ids():
    ids = set()
    listing = subprocess.run(["git", "-C", RA, "ls-tree", "-r", "--name-only", "HEAD",
                              "npc/re/quests/"], capture_output=True, text=True).stdout
    for f in listing.split("\n"):
        if not f.endswith(".txt") or os.path.basename(f)[:-4] in OUT_EPISODES:
            continue
        for mm in re.finditer(r'\b(?:setquest|completequest|checkquest|erasequest|getquest'
                              r'|isbegin_quest|questprogress)\s*[ (]\s*(\d+)', ra_show(f)):
            ids.add(int(mm.group(1)))
    return ids

def parse_questdb_yml(missing):
    """yml -> {id: {'Title':..., 'Time':0, 'Targets':[(aegis,count),...]}} for missing ids."""
    out = {}; cur = None; intargets = False
    for ln in rd(os.path.join(RA, "db", "re", "quest_db.yml")).splitlines():
        m = re.match(r'^\s*-\s*Id:\s*(\d+)', ln)
        if m:
            cur = int(m.group(1))
            if cur in missing:
                out[cur] = {"Title": f"Quest{cur}", "Time": 0, "Targets": []}
            intargets = False
            continue
        if cur not in out:
            continue
        mt = re.match(r'^\s*Title:\s*(.*)$', ln)
        if mt:
            out[cur]["Title"] = mt.group(1).strip().strip('"').replace('"', "'").replace(",", " ")
            continue
        if re.match(r'^\s*Targets:\s*$', ln):
            intargets = True; continue
        if intargets:
            mm = re.match(r'^\s*-\s*Mob:\s*(\S+)', ln)
            if mm:
                out[cur]["Targets"].append([mm.group(1).strip(), 0])
            mc = re.match(r'^\s*Count:\s*(\d+)', ln)
            if mc and out[cur]["Targets"]:
                out[cur]["Targets"][-1][1] = int(mc.group(1))
            if re.match(r'^    \w+:', ln) and not re.match(r'^\s*(Mob|Count):', ln):
                intargets = False
    return out

def to_row(qid, q, aegis2id, droplog):
    """quest dict -> 9-field TXT row."""
    tgt = q["Targets"][:3]
    if len(q["Targets"]) > 3:
        droplog.append(f"{qid}\tdropped {len(q['Targets'])-3} extra targets (max 3)")
    cells = []
    for aegis, cnt in tgt:
        mid = aegis2id.get(aegis.upper())
        if mid is None:
            mid = "0"; droplog.append(f"{qid}\tmob {aegis} absent from mob_db -> target 0")
        cells += [mid, str(cnt)]
    while len(cells) < 6:                              # pad to 3 targets
        cells += ["0", "0"]
    title = q["Title"] or f"Quest{qid}"
    return f'{qid},{q["Time"]},{cells[0]},{cells[1]},{cells[2]},{cells[3]},{cells[4]},{cells[5]},"{title}"'

def emit(rows):
    path = os.path.join(UA, "db", "quest_db.txt")
    txt = rd(path)
    txt = re.sub(re.escape(GEN_HDR) + r".*?" + re.escape(GEN_END) + r"\n?", "", txt, flags=re.S)
    if not txt.endswith("\n"):
        txt += "\n"
    with open(path, "w", encoding="latin-1") as f:
        f.write(txt + GEN_HDR + "\n" + "\n".join(rows) + "\n" + GEN_END + "\n")

def build():
    aegis2id = mob_aegis2id()
    missing = used_quest_ids() - ua_quest_ids()
    qs = parse_questdb_yml(missing)
    droplog = []
    rows = [to_row(qid, qs[qid], aegis2id, droplog) for qid in sorted(qs)]
    return rows, missing, qs, droplog

def selftest():
    a2i = {"PORING": "1002", "ZEROM": "1196"}
    q = {"Title": 'Soloing, "Sphinx"!', "Time": 0, "Targets": [["ZEROM", 20]]}
    row = to_row(1101, q, a2i, [])
    c = row.split(",")
    assert c[0] == "1101" and c[2] == "1196" and c[3] == "20", c     # mob aegis->id, count
    assert c[4] == "0" and c[8].startswith('"') , c                  # padded + quoted title
    assert '","' not in row and "Sphinx" in row, row                 # comma/quote sanitised
    # missing mob -> 0
    row2 = to_row(1, {"Title": "T", "Time": 0, "Targets": [["NOSUCHMOB", 5]]}, a2i, [])
    assert row2.split(",")[2] == "0", row2
    # >3 targets capped
    big = {"Title": "T", "Time": 0, "Targets": [["PORING", 1]] * 5}
    dl = []; r3 = to_row(2, big, a2i, dl)
    assert len(r3.split(",")) == 9 and dl, (r3, dl)
    print("SELFTEST OK")

def main():
    if "--selftest" in sys.argv:
        selftest(); return
    rows, missing, qs, droplog = build()
    print(f"missing quest-IDs: {len(missing)} | in yml: {len(qs)} | rows: {len(rows)} | "
          f"target-drops: {len(droplog)}")
    if "--dry-run" not in sys.argv:
        emit(rows)
        with open(os.path.join(UA, "Doc", "backport_renewal_questdb_drops.txt"),
                  "w", encoding="utf-8") as f:
            f.write("\n".join(droplog) + "\n")
        print("written.")

if __name__ == "__main__":
    main()

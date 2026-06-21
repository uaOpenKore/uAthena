# SP-2 Renewal quests (2-pre quest_db + 2a zone-quests) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backport 1073 renewal quest_db entries, then the 7 zone-quest NPC files that use them, into uAthena.

**Architecture:** Task 1 — yml→TXT converter (`backport-renewal-questdb.py`) appends 1073 quests to `db/quest_db.txt` (mob aegis→id via mob_db). Task 2 — quest-NPC generator (`backport-renewal-quests.py`) assembled exactly like the SP-3 small-NPC generator (town adapt_text + merchant block_filter + quest tail), emits to `npc/backport/re_quests/`. 0 engine changes.

**Tech Stack:** Python 3, uAthena C map-server (`--run_once`), rAthena `/tmp/rathena-ref` (7f08087).

## Global Constraints

- Source pinned: rAthena `7f08087`, `/tmp/rathena-ref`, `db/re/` + `npc/re/` materialized.
- No engine changes. quest_db.txt append-only; NPC output ONLY under `npc/backport/re_quests/`; includes append-only in `npc/scripts_athena.conf` + `conf/maps_athena.conf`.
- Byte-preserving latin-1 for NPC/quest_db TXT; UTF-8 for Doc/ logs.
- All docs → `Doc/`. Before push: `git fetch && git rebase`. Commit footer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Spec: `Doc/backport_renewal_sp2_quests_design.md`. Reuses SP-1/SP-3 assets ([[backport-renewal-content-series]]): `backport-renewal-town-npcs.py` (adapt_text) + `backport-renewal-merchants.py` (block_filter etc).

**Measured facts:** 1075 missing quest-IDs (across all IN quest files), 1073 in rAthena quest_db.yml. quest_db.txt format: `ID,Time,Target1,Val1,Target2,Val2,Target3,Val3,"Title"` (9 fields, ≤3 mob targets). yml Targets: `Mob: <AEGIS>` + `Count: N`. 2a = 7 zone files (~59K). token-gap 26 (covered by adapt_text CLASS E + block_filter UNRESOLVED). OUT: episodes 14.3-18.

---

## File Structure

**Created:** `dumps/forge/backport-renewal-questdb.py`, `dumps/forge/backport-renewal-quests.py`, `npc/backport/re_quests/*.txt`, `Doc/backport_renewal_quests_gap.md`, `Doc/backport_renewal_sp2_quests_changes.md`, `dumps/forge/backport-renewal-quests-includes.txt`, `dumps/forge/backport-renewal-quests-maps.txt`.
**Modified (append-only):** `db/quest_db.txt`, `npc/scripts_athena.conf`, `conf/maps_athena.conf`.

---

## Task 1 (2-pre): quest_db converter

**Files:**
- Create: `dumps/forge/backport-renewal-questdb.py`
- Modify: `db/quest_db.txt` (append)

**Interfaces:**
- Produces: 1073 quest rows appended to `db/quest_db.txt` between GENERATED markers (idempotent).

- [ ] **Step 1: Write the converter with selftest fixtures (test-first)**

Create `dumps/forge/backport-renewal-questdb.py`:

```python
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
```

- [ ] **Step 2: Selftest**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-questdb.py --selftest`
Expected: `SELFTEST OK`

- [ ] **Step 3: Dry-run**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-questdb.py --dry-run`
Expected: `missing quest-IDs: ~1075 | in yml: ~1073 | rows: ~1073 | target-drops: N`

- [ ] **Step 4: Generate**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-questdb.py`
Expected: report + `written.`. `git diff --stat db/quest_db.txt` shows +~1075 lines.

- [ ] **Step 5: Boot quest_db-load verify**

```bash
cd /root/uAthena && set +e
timeout 120 ./map-server_sql --run_once > /tmp/q_boot.log 2>&1
echo "exit: $? | quest_db read:"; grep -iE "quest.*db|Done reading.*quest" /tmp/q_boot.log | head -2
grep -icE "quest.*error|invalid quest" /tmp/q_boot.log
grep -iE "Server is 'ready'" /tmp/q_boot.log | tail -1
set -e
```
Expected: server ready; 0 quest-db parse errors. (Targets with id 0 are valid no-op objectives.)

- [ ] **Step 6: Commit**

```bash
cd /root/uAthena && git fetch && git rebase
git add dumps/forge/backport-renewal-questdb.py db/quest_db.txt Doc/backport_renewal_questdb_drops.txt
git commit -m "$(cat <<'EOF'
backport: 1073 renewal quest_db entries -> quest_db.txt [renewal-quests]

Converter dumps/forge/backport-renewal-questdb.py (yml->TXT 9-field, mob aegis->id via
mob_db, <=3 targets). Quest-IDs used by IN renewal quests, missing from uAthena quest_db.
Foundation for SP-2 quest NPCs. 0 engine changes. Boot quest_db-load clean.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2 (2a): zone-quest generator

**Files:**
- Create: `dumps/forge/backport-renewal-quests.py`
- Create (generated): `npc/backport/re_quests/*.txt`, gap log, includes, maps
- Modify: `npc/scripts_athena.conf`, `conf/maps_athena.conf`

**Interfaces:**
- Consumes: `db/quest_db.txt` (after Task 1); town adapt_text + merchant block_filter (assembled in, identical to SP-3).
- Produces: adapted zone-quest NPCs under `re_quests/`.

- [ ] **Step 1: Write the quest-specific tail (`/tmp/quests_specific.py`)**

This is the SP-3 small-NPC tail with the file-list changed to the 2a zone files and `OUT_DIR` = `re_quests`. Content:

```python
# ---- SP-2 2a zone-quest specifics ----
OUT_DIR = os.path.join("npc", "backport", "re_quests")
ZONE_2A = ["eclage", "malangdo", "malaya", "dicastes", "rockridge", "mora", "dewata"]
HEADER = ("//===== uAthena backport (renewal quests 2a, GENERATED) =====\n"
          "//= zone-quests from rathena-ref; tokens adapted, renewal-feature blocks commented.\n"
          "//= DO NOT EDIT - regenerate via dumps/forge/backport-renewal-quests.py\n"
          "//= Source: {src}\n"
          "//============================================================\n")

def quest_sources():
    return [f"npc/re/quests/quests_{z}.txt" for z in ZONE_2A]

def defined_in(body):
    s = set()
    for ln in body.split("\n"):
        if ln.strip().startswith("//"):
            continue
        f = ln.split("\t")
        if len(f) >= 3 and (("," in f[0] and not f[0].startswith("//")) or f[0] in ("function", "-")):
            if f[1] in ("script", "shop", "cashshop", "function") or f[1].startswith("duplicate("):
                nm = f[2]; s.add(nm.split("::")[0].strip())
                if "::" in nm:
                    s.add(nm.split("::", 1)[1].strip())
    return s

def gen():
    gap_buf = ["# Renewal 2a zone-quest gap-лог (адаптации/dedup/boundary/unresolved/orphan)\n\n"]
    includes = []; total = Counter()
    bodies = {}; all_events = {}
    for rel in quest_sources():
        body, events = adapt_merchant_text(ra_show(rel))
        name = os.path.basename(rel)
        bodies[name] = body; all_events[name] = events
    # uAthena has no direct paren-call to script functions (only buildins / callfunc()).
    # Rewrite Name(args) -> callfunc("Name",args) for every user-function (function script
    # Name) defined across the bodies. Empty-paren Name() -> callfunc("Name").
    userfuncs = set()
    for body in bodies.values():
        for m in re.finditer(r'^function\tscript\t(\w+)\t', body, re.M):
            userfuncs.add(m.group(1))
    for nm in bodies:
        body = bodies[nm]
        for fn in userfuncs:
            body = re.sub(r'(?<![."\w])' + re.escape(fn) + r'\s*\(\s*\)', f'callfunc("{fn}")', body)
            body = re.sub(r'(?<![."\w])' + re.escape(fn) + r'\s*\(', f'callfunc("{fn}",', body)
        bodies[nm] = body
    live = set(EXIST_NAMES)
    for body in bodies.values():
        live |= defined_in(body)
    live.discard("")
    for name in bodies:
        body = bodies[name]; ev = all_events[name]
        out2 = []
        for ln in body.split("\n"):
            mm = re.search(r'duplicate\(([^)]+)\)', ln)
            if mm and mm.group(1).strip() not in live and not ln.strip().startswith("//"):
                out2.append("//[BACKPORT-ORPHAN:" + mm.group(1).strip() + "] " + ln)
                ev.append(("ORPHAN", mm.group(1).strip(), ln.strip()))
            else:
                out2.append(ln)
        body = "\n".join(out2)
        write_raw(os.path.join(UA_ROOT, OUT_DIR, name),
                  HEADER.format(src="npc/re/quests/" + name) + body +
                  ("" if body.endswith("\n") else "\n"))
        includes.append(f"npc: npc/backport/re_quests/{name}")
        if ev:
            gap_buf.append(f"\n## {name}\n")
            for kind, tok, ln in ev:
                total[kind] += 1
                gap_buf.append(f"- {kind} [{tok}] {ln}\n")
    used = set()
    for p in glob.glob(os.path.join(UA_ROOT, OUT_DIR, "*.txt")):
        for ln in read(p).splitlines():
            s = ln.strip()
            if not s or s.startswith("//") or s.startswith("function"):
                continue
            c = ln.split("\t")
            if "," in c[0] and not c[0].startswith("-"):
                used.add(c[0].split(",")[0])
    scope_maps = sorted(m for m in used if m in UA_MAPS)
    write(os.path.join(UA_ROOT, "dumps", "forge", "backport-renewal-quests-maps.txt"),
          "\n".join("map: " + m for m in scope_maps) + "\n")
    write(os.path.join(UA_ROOT, "Doc", "backport_renewal_quests_gap.md"), "".join(gap_buf))
    write(os.path.join(UA_ROOT, "dumps", "forge", "backport-renewal-quests-includes.txt"),
          "\n".join(includes) + "\n")
    print(f"files: {len(includes)} | events: {dict(total)}")

def backport_files():
    return sorted(glob.glob(os.path.join(UA_ROOT, OUT_DIR, "*.txt")))

def verify():
    mi = set()
    for ln in read(os.path.join(UA_ROOT, "db", "map_index.txt")).splitlines():
        x = ln.strip()
        if x and not x.startswith("//"):
            mi.add(x.split()[0])
    defined = set()
    for p in glob.glob(os.path.join(UA_ROOT, "npc", "**", "*.txt"), recursive=True):
        for n in defined_names(read(p)):
            defined.add(n)
    miss_cmd, brace_bad, miss_ref, unreg = set(), [], set(), set()
    for p in backport_files():
        t = read(p)
        nc = "\n".join(l for l in t.splitlines() if not l.strip().startswith("//"))
        for ln in nc.splitlines():
            miss_cmd |= ({x.upper() for x in re.findall(r'[A-Za-z_]\w*', code_only(ln))} & GAP_BUILTINS)
        if code_only(nc).count("{") != code_only(nc).count("}"):
            brace_bad.append(os.path.relpath(p, UA_ROOT))
        for r in references(nc):
            if r not in defined:
                miss_ref.add(r)
        for s, f in def_lines(t):
            if f[0].split(",")[0] not in mi:
                unreg.add(f[0].split(",")[0])
    print(f"live gap commands: {sorted(c.lower() for c in miss_cmd) or 'none'}")
    print(f"unresolved refs: {sorted(miss_ref)[:20] or 'none'}")
    print(f"unregistered maps: {sorted(unreg) or 'none'}")
    print(f"brace-imbalanced: {brace_bad or 'none'}")
    ok = not (miss_cmd or brace_bad or unreg)
    print("VERIFY", "OK" if ok else "FAILED")
    return ok

def main():
    if "--selftest" in sys.argv:
        assert len(quest_sources()) == 7, quest_sources()
        assert "DUPLICATE" not in GAP_BUILTINS
        print("SELFTEST OK"); return
    if "--verify" in sys.argv:
        sys.exit(0 if verify() else 1)
    gen(); print("written.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Assemble + selftest**

```bash
cd /root/uAthena
python3 - <<'ASM'
town=open('dumps/forge/backport-renewal-town-npcs.py',encoding='utf-8').read().replace('\nif __name__ == "__main__":\n    main()\n','\n')
merch=open('dumps/forge/backport-renewal-merchants.py',encoding='utf-8').read()
ms=merch.index('def ua_item_ids'); me=merch.index('def gen(', ms)   # gen AFTER ua_item_ids
small=open('/tmp/quests_specific.py',encoding='utf-8').read()
open('dumps/forge/backport-renewal-quests.py','w',encoding='utf-8').write(town+'\nimport subprocess\n'+merch[ms:me]+'\n'+small)
print("assembled")
ASM
UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-quests.py --selftest
```
Expected: `assembled` + `SELFTEST OK`. (Same assembly mechanism as SP-3; the merchant slice provides adapt_merchant_text/block_filter/EXIST_NAMES/ra_show.)

- [ ] **Step 3: Generate + verify**

```bash
cd /root/uAthena
UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-quests.py
UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-quests.py --verify
```
Expected: `files: 7 | events: {...}` then `VERIFY OK`. If `live gap commands` non-empty → extend adapt_text (town-npcs.py) and re-assemble. If `unregistered maps` non-empty → block_filter BOUNDARY should have commented them; confirm map not in map_index.

- [ ] **Step 4: Wire + boot-parse**

```bash
cd /root/uAthena
grep -q "Backport renewal quests" npc/scripts_athena.conf || { echo ""; echo "// ===== Backport renewal quests 2a (GENERATED) ====="; cat dumps/forge/backport-renewal-quests-includes.txt; } >> npc/scripts_athena.conf
grep -q "Backport renewal quest maps" conf/maps_athena.conf || { echo ""; echo "// ===== Backport renewal quest maps (GENERATED) ====="; cat dumps/forge/backport-renewal-quests-maps.txt; } >> conf/maps_athena.conf
set +e; timeout 120 ./map-server_sql --run_once > /tmp/sp2a_boot.log 2>&1
echo "exit: $? | errors on re_quests: $(grep -cE 'script error on npc/backport/re_quests' /tmp/sp2a_boot.log) | bad-dup: $(grep -icE 'bad duplicate.*re_quests' /tmp/sp2a_boot.log)"
grep -iE "Server is 'ready'" /tmp/sp2a_boot.log; set -e
```
Expected: `exit: 0`, 0 errors on `re_quests`, Server ready. Iterate (extend adapt_text/block_filter) until 0.

- [ ] **Step 5: Write change summary + commit**

Create `Doc/backport_renewal_sp2_quests_changes.md` (counts: 1073 quest_db + 7 zone files live, DEDUP/BOUNDARY/UNRESOLVED/ORPHAN, tester notes). Then:
```bash
cd /root/uAthena && git fetch && git rebase
git add dumps/forge/backport-renewal-quests.py npc/backport/re_quests/ \
        dumps/forge/backport-renewal-quests-includes.txt dumps/forge/backport-renewal-quests-maps.txt \
        Doc/backport_renewal_quests_gap.md Doc/backport_renewal_sp2_quests_changes.md \
        npc/scripts_athena.conf conf/maps_athena.conf
git commit -m "$(cat <<'EOF'
backport: renewal 2a zone-quests -> npc/backport/re_quests/ [renewal-quests]

Generator reuses SP-1/SP-3 adapt_text + block_filter. 7 zone-quest files (eclage/
malangdo/malaya/dicastes/rockridge/mora/dewata) on the 1073-entry quest_db foundation.
Verify OK, --run_once 0 script errors.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**1. Spec coverage:** 2-pre quest_db (1073, yml→TXT, mob aegis→id, ≤3 targets) → Task 1. 2a zone-quests (7 files, generator reuse) → Task 2. token-gap → adapt_text/block_filter (assembled). Isolation/verify/boot → both tasks. OUT episodes → excluded in `OUT_EPISODES`/`quest_sources()`.

**2. Placeholder scan:** No TBD; converter is complete; Task 2 reuses the proven SP-3 assembly (exact slice anchors `def ua_item_ids`..`def gen(`).

**3. Type consistency:** Task 1 `mob_aegis2id`/`parse_questdb_yml`/`to_row(qid,q,aegis2id,droplog)`/`emit` consistent. Task 2 `quest_sources`/`defined_in`/`gen`/`verify` mirror SP-3; `adapt_merchant_text`/`block_filter`/`EXIST_NAMES`/`ra_show`/`code_only`/`def_lines`/`references`/`defined_names`/`UA_MAPS`/`GAP_BUILTINS`/`write_raw`/`read`/`write` from the town+merchant paste.

**Known follow-ups:** renewal-feature quest blocks (clear/sit/delequip/mesitemlink/questinfo/charat) UNRESOLVED-commented (logged); 2b/2c/2d are separate sub-phases reusing the same generator with a different file-list.

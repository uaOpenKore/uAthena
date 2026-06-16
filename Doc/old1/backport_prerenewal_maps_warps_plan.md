# Pre-renewal Maps/Warps Backport — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Additively backport pre-renewal locations and warps from `/tmp/eathena-ref` into uAthena, keeping every existing warp/coordinate unchanged and documenting all rejected entry/exit points for testers.

**Architecture:** A single deterministic Python generator (`dumps/forge/backport-warps.py`) reads both warp trees, applies the merge rules (name-collision OR tile-collision → keep uAthena + record conflict; else add), and emits new warp files under `npc/warps/backport/`, a conflict document, `map_index` additions, and `scripts_warps.conf` include lines. Existing files are never modified except two guarded appends (`db/map_index.txt`, `npc/scripts_warps.conf`).

**Tech Stack:** Python 3 (build-time tool only, not shipped), uAthena warp scripts, `db/map_index.txt`.

**Design spec:** `doc/backport_prerenewal_maps_warps_design.md` (committed `5132ae7`).

**Branch:** `x64`. Run all commands from repo root `/root/uAthena`.

---

## File Structure

- **Create** `dumps/forge/backport-warps.py` — the generator (parse, merge, emit, selftest, verify). Single responsibility: produce all backport artifacts deterministically.
- **Create (generated)** `npc/warps/backport/<subdir>/<file>.txt` — new warps only, mirroring eathena-ref's `npc/warps/` subdir layout.
- **Create (generated)** `doc/backport_warp_conflicts.md` — ВХОД/ВЫХОД rejected points with `решение?` placeholders.
- **Create (generated)** `dumps/forge/backport-mapindex-additions.txt`, `dumps/forge/backport-scripts_warps-includes.txt` — splice sources.
- **Modify (guarded append only)** `db/map_index.txt`, `npc/scripts_warps.conf`.
- **Create** `doc/backport_maps_warps_changes.md` — tester-facing change summary + checklist.

Existing `npc/warps/**` files and the active part of `db/map_index.txt` are **never edited**.

---

## Task 1: Generator script with selftest (TDD)

**Files:**
- Create: `dumps/forge/backport-warps.py`

- [ ] **Step 1: Write the generator with a STUB `classify` and a built-in selftest**

Create `dumps/forge/backport-warps.py` with exactly this content (note `classify` is a stub that returns empty results — it is implemented in Step 3):

```python
#!/usr/bin/env python3
"""Additive pre-renewal maps/warps backport: eathena-ref -> uAthena.

Applies the additive merge rules from
doc/backport_prerenewal_maps_warps_design.md and emits (under repo root):
  npc/warps/backport/<subdir>/<file>.txt           new warps only
  doc/backport_warp_conflicts.md                   ВХОД/ВЫХОД rejected points
  dumps/forge/backport-mapindex-additions.txt      new db/map_index.txt lines
  dumps/forge/backport-scripts_warps-includes.txt  scripts_warps.conf lines

Modes:
  --selftest   run built-in fixtures, assert merge rules
  --dry-run    compute + print report, write nothing
  --verify     scan npc/ (incl. backport) for duplicate names / tile collisions
  (no flag)    generate all outputs

Idempotent: regenerates backport/** and docs from scratch. Run from repo root.
"""
import os, re, sys, glob
from collections import Counter

UA_ROOT = os.environ.get("UA_ROOT", ".")
EA_ROOT = os.environ.get("EA_ROOT", "/tmp/eathena-ref")

# In-scope NEW content by explicit name (design doc §3).
INSCOPE_NAMES = set("""
moc_fild20 moc_fild21 moc_fild22 moc_fild22b moc_prydn1 moc_prydn2 moc_para01
moscovia mosk_dun
brasilis bra_fild01 bra_dun01 bra_dun02 bra_in01
manuk man_fild01 man_fild02 man_fild03 man_in01 mid_camp mid_campin
splendide spl_fild01 spl_fild02 spl_fild03 spl_in01 spl_in02
aru_gld arug_cas01 arug_cas02 arug_cas03 arug_cas04 arug_cas05 arug_dun01 schg_dun01
mora bif_fild01 bif_fild02
""".split())

# Renewal-towns registered by prefix (map_index only; ~0 static warps). Matched
# against the NEW-map set so excluded/instance maps can't sneak in.
INSCOPE_PREFIXES = ("dicastes","dic_","eclage","ecl_","dewata","dew_",
                    "malangdo","mal_","malaya","ma_fild","ma_dun","ma_in",
                    "ma_scene","ma_zif")

def parse_warp(line):
    """src(map,x,y[,dir]) <ws> warp <ws> name <ws> xs,ys,dstmap,dx,dy -> dict|None."""
    s = line.strip()
    if not s or s.startswith("//"):
        return None
    p = re.split(r'[\t ]+', s)
    if len(p) < 4 or p[1] != "warp":
        return None
    src = p[0].split(","); rhs = p[3].split(",")
    if len(src) < 3 or len(rhs) < 5:
        return None
    try:
        x, y = int(src[1]), int(src[2]); dx, dy = int(rhs[3]), int(rhs[4])
    except ValueError:
        return None
    return {"srcmap":src[0], "x":x, "y":y, "facing":src[3] if len(src)>3 else "0",
            "name":p[2], "xs":rhs[0], "ys":rhs[1], "dstmap":rhs[2], "dx":dx, "dy":dy}

def load_warps(root, subtree, include_backport=False):
    out = []
    for path in glob.glob(os.path.join(root, subtree, "**", "*.txt"), recursive=True):
        if not include_backport and "/backport/" in path.replace("\\","/"):
            continue
        with open(path, encoding="latin-1") as f:
            for line in f:
                w = parse_warp(line)
                if w:
                    w["file"] = path
                    out.append(w)
    return out

def load_mapindex(path):
    s = set()
    with open(path, encoding="latin-1") as f:
        for line in f:
            t = line.strip()
            if t and not t.startswith("//"):
                s.add(t.split()[0])
    return s

def in_scope(m, new_maps):
    return m in INSCOPE_NAMES or (m in new_maps and m.startswith(INSCOPE_PREFIXES))

def classify(ua_warps, ea_warps, new_maps):
    return {}, {}, []   # STUB — implemented in Task 1 Step 3

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="latin-1") as f:
        f.write(content)

def emit(added, conflicts, register):
    includes = []
    for rel in sorted(added):
        lines = sorted(set(added[rel]))
        hdr = ("//===== uAthena backport (GENERATED) =========================\n"
               "//= Additive pre-renewal warps from eathena-ref.\n"
               "//= DO NOT EDIT - regenerate via dumps/forge/backport-warps.py\n"
               f"//= Source: npc/warps/{rel}\n"
               "//============================================================\n")
        write_file(os.path.join(UA_ROOT, "npc", "warps", "backport", rel),
                   hdr + "\n".join(lines) + "\n")
        includes.append(f"npc: npc/warps/backport/{rel}")
    buf = ["# Конфликты варпов бэкпорта (отвергнутые точки)\n\n",
           "Тестировщики: замените `решение?` корректирующими данными.\n",
           "Схема — doc/backport_prerenewal_maps_warps_design.md §5.\n"]
    for m in sorted(conflicts):
        c = conflicts[m]
        buf.append(f"\n## {m}\n")
        buf.append("# ВХОД: требуемая(карта,x,y) -> на_новой(карта,x,y) | СОХРАНЁН старый | решение?\n")
        buf += [e + "\n" for e in sorted(set(c["vhod"]))]
        buf.append("# ВЫХОД: на_новой(карта,x,y) -> на_старой(карта,x,y) | примечание | решение?\n")
        buf += [e + "\n" for e in sorted(set(c["vyhod"]))]
    write_file(os.path.join(UA_ROOT, "doc", "backport_warp_conflicts.md"), "".join(buf))
    write_file(os.path.join(UA_ROOT, "dumps", "forge", "backport-mapindex-additions.txt"),
               "// ===== Backport pre-renewal locations (GENERATED) =====\n"
               + "".join(m + "\n" for m in register))
    write_file(os.path.join(UA_ROOT, "dumps", "forge", "backport-scripts_warps-includes.txt"),
               "\n".join(includes) + "\n")

def report(added, conflicts, register):
    na = sum(len(v) for v in added.values())
    nv = sum(len(c["vhod"]) for c in conflicts.values())
    nx = sum(len(c["vyhod"]) for c in conflicts.values())
    print(f"register maps: {len(register)} | added warps: {na} in {len(added)} files | "
          f"VHOD: {nv} | VYHOD: {nx} | conflict maps: {len(conflicts)}")

def real_data():
    ua = load_warps(UA_ROOT, "npc")
    ea = load_warps(EA_ROOT, os.path.join("npc", "warps"))
    new_maps = load_mapindex(os.path.join(EA_ROOT, "db", "map_index.txt")) - \
               load_mapindex(os.path.join(UA_ROOT, "db", "map_index.txt"))
    return classify(ua, ea, new_maps)

def selftest():
    new = {"moc_fild20", "moc_fild22b"}
    ua = [parse_warp("moc_fild01,101,16,0\twarp\tmocf01-1\t15,3,moc_fild04,317,376"),
          parse_warp("moc_fild04,213,327,0\twarp\tant001\t1,1,anthell01,35,267")]
    ea = [parse_warp("moc_fild01,101,16,0\twarp\tmocf01-1\t15,3,moc_fild20,210,342"),
          parse_warp("moc_fild21,26,196,0\twarp\tmocf020\t1,1,moc_fild20,349,179"),
          parse_warp("moc_fild20,156,143,0\twarp\tant001\t1,1,anthell01,35,263")]
    added, conflicts, register = classify(ua, ea, new)
    assert "moc_fild22b" in register, register
    assert sum(len(v) for v in added.values()) == 1, added
    assert len(conflicts["moc_fild20"]["vhod"]) == 1, conflicts
    assert len(conflicts["moc_fild20"]["vyhod"]) == 1, conflicts
    print("SELFTEST OK")

def verify():
    allw = load_warps(UA_ROOT, "npc", include_backport=True)
    bp = [w for w in allw if "/backport/" in w["file"].replace("\\","/")]
    nonbp = [w for w in allw if "/backport/" not in w["file"].replace("\\","/")]
    nonbp_names = Counter(w["name"] for w in nonbp)
    bp_names = Counter(w["name"] for w in bp)
    nonbp_tiles = {(w["srcmap"], w["x"], w["y"]) for w in nonbp}
    bad_names = [(n, k, nonbp_names.get(n, 0)) for n, k in bp_names.items()
                 if k > 1 or nonbp_names.get(n, 0) > 0]
    bad_tiles = [w for w in bp if (w["srcmap"], w["x"], w["y"]) in nonbp_tiles]
    print(f"backport warps: {len(bp)} | dup-name issues: {len(bad_names)} | tile collisions: {len(bad_tiles)}")
    for b in bad_names[:50]: print("   DUPNAME", b)
    for w in bad_tiles[:50]: print("   TILE", w["srcmap"], w["x"], w["y"], w["name"])
    ok = not bad_names and not bad_tiles
    print("VERIFY", "OK" if ok else "FAILED")
    return ok

def main():
    if "--selftest" in sys.argv:
        selftest(); return
    if "--verify" in sys.argv:
        sys.exit(0 if verify() else 1)
    added, conflicts, register = real_data()
    report(added, conflicts, register)
    if "--dry-run" not in sys.argv:
        emit(added, conflicts, register)
        print("written.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the selftest to verify it FAILS (stub classify)**

Run: `python3 dumps/forge/backport-warps.py --selftest`
Expected: `AssertionError` (the stub returns empty `register`, so `assert "moc_fild22b" in register` fails).

- [ ] **Step 3: Implement `classify` (replace the stub)**

Replace the stub `def classify(...): return {}, {}, []` line with:

```python
def classify(ua_warps, ea_warps, new_maps):
    ua_names, ua_tiles = {}, {}
    for w in ua_warps:
        ua_names.setdefault(w["name"], w)
        ua_tiles.setdefault((w["srcmap"], w["x"], w["y"]), w)
    added, conflicts = {}, {}
    for w in ea_warps:
        s, d = w["srcmap"], w["dstmap"]
        if not (in_scope(s, new_maps) or in_scope(d, new_maps)):
            continue
        hit = ua_names.get(w["name"]) or ua_tiles.get((s, w["x"], w["y"]))
        if hit:
            ref = (f'{hit["name"]}: {hit["srcmap"]},{hit["x"]},{hit["y"]}'
                   f'->{hit["dstmap"]},{hit["dx"]},{hit["dy"]}')
            head = f'{s},{w["x"]},{w["y"]} -> {d},{w["dx"]},{w["dy"]}'
            if in_scope(d, new_maps):
                conflicts.setdefault(d, {"vhod": [], "vyhod": []})["vhod"].append(
                    f'{head} | СОХРАНЁН {ref} | решение?')
            else:
                conflicts.setdefault(s, {"vhod": [], "vyhod": []})["vyhod"].append(
                    f'{head} | конфликт со старым {ref} | решение?')
            continue
        rel = os.path.relpath(w["file"], os.path.join(EA_ROOT, "npc", "warps")).replace("\\", "/")
        added.setdefault(rel, []).append(
            f'{s},{w["x"]},{w["y"]},{w["facing"]}\twarp\t{w["name"]}\t'
            f'{w["xs"]},{w["ys"]},{d},{w["dx"]},{w["dy"]}')
    # Register: in-scope new maps PLUS any new map that is an endpoint of an added
    # warp (guarantees no added warp references an unregistered map).
    register = set(m for m in new_maps if in_scope(m, new_maps))
    for lines in added.values():
        for ln in lines:
            cols = ln.split("\t")
            for m in (cols[0].split(",")[0], cols[3].split(",")[2]):
                if m in new_maps:
                    register.add(m)
    return added, conflicts, sorted(register)
```

- [ ] **Step 4: Run the selftest to verify it PASSES**

Run: `python3 dumps/forge/backport-warps.py --selftest`
Expected: `SELFTEST OK`

- [ ] **Step 5: Dry-run on REAL data and sanity-check the report**

Run: `python3 dumps/forge/backport-warps.py --dry-run`
Expected: a single report line, e.g. `register maps: N | added warps: M in K files | VHOD: ... | VYHOD: ... | conflict maps: ...`.
Sanity: `register` should be in the low hundreds (renewal towns + new geography), `added warps` should be > 150 (Manuk/Splendide dominate), and conflict maps should include `moc_fild20`. If `added warps` is 0 or `register` is 0, stop and debug paths (`EA_ROOT`, `UA_ROOT`).

- [ ] **Step 6: Commit the generator**

```bash
git add dumps/forge/backport-warps.py
git commit -m "backport: deterministic pre-renewal warp/map merge generator

Reads uAthena + eathena-ref warp trees, applies additive merge rules
(name/tile collision -> keep uAthena + record ВХОД/ВЫХОД conflict; else add).
--selftest covers the merge rules on fixtures; --verify checks uniqueness.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Generate and commit backport artifacts

**Files:**
- Create (generated): `npc/warps/backport/**/*.txt`, `doc/backport_warp_conflicts.md`, `dumps/forge/backport-mapindex-additions.txt`, `dumps/forge/backport-scripts_warps-includes.txt`

- [ ] **Step 1: Generate all outputs**

Run: `python3 dumps/forge/backport-warps.py`
Expected: report line then `written.`

- [ ] **Step 2: Inspect the moc_fild20 conflict section (showcase)**

Run: `sed -n '/## moc_fild20/,/## /p' doc/backport_warp_conflicts.md | head -40`
Expected: a `## moc_fild20` section with ВХОД lines like
`moc_fild01,101,16 -> moc_fild20,210,342 | СОХРАНЁН mocf01-1: moc_fild01,101,16->moc_fild04,317,376 | решение?`
and each line ending in `решение?`.

- [ ] **Step 3: Inspect generated warp files and map_index additions**

Run: `find npc/warps/backport -name '*.txt' | sort && echo '---' && head -20 dumps/forge/backport-mapindex-additions.txt`
Expected: backport warp files mirroring eathena-ref subdirs (e.g. `fields/morroc_fild.txt`, `fields/man_fild.txt`, `fields/spl_fild.txt`, `cities/...`, `guild/...`); the additions file lists new map names (e.g. `moc_fild22b`, `manuk`, `splendide`, `dicastes01`, ...).

- [ ] **Step 4: Confirm no in-scope renewal-system maps leaked in (negative check)**

Run: `grep -E '^(bat_|1@|2@|[3-6]@|te_|teg_dun|job3_|que_|iz_|izlude_[a-d]|gld2_|e_tower|nyd_dun|jupe_core2|evt_|new_event|s_atelier|job_ko)' dumps/forge/backport-mapindex-additions.txt && echo 'LEAK FOUND' || echo 'clean'`
Expected: `clean` (no excluded-class map was registered).

- [ ] **Step 5: Commit the generated artifacts**

```bash
git add npc/warps/backport doc/backport_warp_conflicts.md \
        dumps/forge/backport-mapindex-additions.txt \
        dumps/forge/backport-scripts_warps-includes.txt
git commit -m "backport: generated pre-renewal warp files, conflict doc, splice sources

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Register locations and wire in warp files (guarded appends)

**Files:**
- Modify (append only): `db/map_index.txt`, `npc/scripts_warps.conf`

- [ ] **Step 1: Append new locations to `db/map_index.txt` (guarded, idempotent)**

Run:
```bash
grep -q 'Backport pre-renewal locations' db/map_index.txt \
  && echo 'already present, skipping' \
  || { printf '\n' >> db/map_index.txt; cat dumps/forge/backport-mapindex-additions.txt >> db/map_index.txt; echo appended; }
```
Expected: `appended` (first run).

- [ ] **Step 2: Verify map_index has no duplicate non-comment entries**

Run: `grep -vE '^\s*//|^\s*$' db/map_index.txt | awk '{print $1}' | sort | uniq -d`
Expected: empty output (no duplicate map names). If any line prints, a backported name duplicates an existing entry — remove it from `dumps/forge/backport-mapindex-additions.txt`'s source list (it was already registered) and re-run Task 2 Step 1 + Task 3 Step 1.

- [ ] **Step 3: Append warp-file includes to `npc/scripts_warps.conf` (guarded)**

Run:
```bash
grep -q 'npc/warps/backport/' npc/scripts_warps.conf \
  && echo 'already present, skipping' \
  || { printf '\n// ===== Backport pre-renewal warps (GENERATED includes) =====\n' >> npc/scripts_warps.conf; cat dumps/forge/backport-scripts_warps-includes.txt >> npc/scripts_warps.conf; echo appended; }
```
Expected: `appended`.

- [ ] **Step 4: Confirm existing files were only appended to (no edits above)**

Run: `git diff --stat db/map_index.txt npc/scripts_warps.conf`
Then: `git diff db/map_index.txt | grep '^-' | grep -v '^---'`
Expected: the stat shows only insertions; the second command prints nothing (no removed/changed lines — append-only).

- [ ] **Step 5: Commit the wiring**

```bash
git add db/map_index.txt npc/scripts_warps.conf
git commit -m "backport: register pre-renewal locations + include backport warp files

Append-only: new map_index entries + scripts_warps.conf includes. Existing
entries unchanged.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Verification

**Files:** none (read-only checks; fix upstream and regenerate if a check fails)

- [ ] **Step 1: NPC-name uniqueness + tile-collision check across all of `npc/`**

Run: `python3 dumps/forge/backport-warps.py --verify`
Expected: `VERIFY OK` (0 duplicate-name issues, 0 tile collisions between backport and existing warps).
If `VERIFY FAILED`: the printed `DUPNAME`/`TILE` lines identify offenders. Duplicate names mean eathena-ref itself defined the same warp name in two in-scope files — pick the correct one (rename or drop) by editing the generator's handling, then regenerate (Task 2) and re-wire (Task 3) before committing.

- [ ] **Step 2: Confirm zero changes to existing warp files**

Run: `git diff --stat HEAD~3 -- npc/warps ':(exclude)npc/warps/backport'`
Expected: empty (no existing `npc/warps/**` file outside `backport/` was touched across the three backport commits).

- [ ] **Step 3: Every backport warp endpoint is a registered map (offline, strong)**

Run:
```bash
python3 - <<'EOF'
import glob, re
mi = set()
for line in open('db/map_index.txt', encoding='latin-1'):
    t = line.strip()
    if t and not t.startswith('//'):
        mi.add(t.split()[0])
bad = set()
for p in glob.glob('npc/warps/backport/**/*.txt', recursive=True):
    for line in open(p, encoding='latin-1'):
        s = line.strip()
        if not s or s.startswith('//'):
            continue
        pp = re.split(r'[\t ]+', s)
        if len(pp) < 4 or pp[1] != 'warp':
            continue
        for m in (pp[0].split(',')[0], pp[3].split(',')[2]):
            if m not in mi:
                bad.add(m)
print('unregistered maps referenced by backport warps:', sorted(bad) or 'none')
EOF
```
Expected: `none`. If any map prints, it is referenced by a backport warp but missing from `db/map_index.txt` — add it to `INSCOPE_NAMES` in the generator (or it should already exist), then regenerate (Task 2) and re-wire map_index (Task 3 Step 1) before continuing. (The generator's endpoint-registration makes this pass by construction; this step is the safety net.)

- [ ] **Step 4 (optional): Best-effort startup scan**

Run: `timeout 25 ./map-server_sql 2>&1 | grep -iE '(warp|map_index).*(error|fail|dupli)' | head` (the server will not fully boot without a char-server; this only scans whatever early output appears)
Expected: no matching lines. Full in-game traversal of every warp is the testers' phase (see the changes doc).

- [ ] **Step 5: No commit unless a check forced a fix.** If Steps 1–4 are clean, proceed to Task 5. If a fix was needed, it was already committed via the regenerate cycle.

---

## Task 5: Tester-facing change document

**Files:**
- Create: `doc/backport_maps_warps_changes.md`

- [ ] **Step 1: Write the changes + verification document**

Create `doc/backport_maps_warps_changes.md`. Fill the bracketed counts from Task 1 Step 5 / Task 2 report output:

```markdown
# Бэкпорт локаций и варпов из дореневала — что изменено и что проверять

## Что изменено
- Добавлены **новые карты** (регистрация в `db/map_index.txt`, append-only): разрушенный Morroc
  (`moc_fild22b`, `moc_prydn1/2`, `moc_para01`), Moscovia (`mosk_dun`), Brasilis (`brasilis`,
  `bra_*`), Новый Мир — Manuk (`manuk`, `man_*`, `mid_camp(in)`) и Splendide (`splendide`, `spl_*`),
  WoE:SE Arunafeltz (`aru_gld`, `arug_cas01-05`, `arug_dun01`, `schg_dun01`), реневал-города
  (Dicastes/Eclage/Dewata/Malangdo/Malaya/Mora) — всего [N] карт.
- Добавлены **новые варпы** ([M] шт.) в изолированном `npc/warps/backport/**`; подключены через
  `npc/scripts_warps.conf`. **Существующие варпы и координаты не менялись** (включая `anthell`).
- **Не добавлялись**: Battlegrounds, инстансы, WoE:TE, Izlude-R/Академия, 3rd-job, квест-инстансы,
  копии `gld2_*` (нет статических варпов / движок вне объёма / вне эпохи).

## Важные ограничения
- Карты читаются из GRF — у клиента тестировщиков должны быть `.gat` новых карт, иначе вход = дисконнект.
- Реневал-города достижимы только через квест-NPC — их вход появится с **портом NPC** (отдельная задача).
  Сейчас они зарегистрированы как локации, но статических варпов в них нет.
- Индексы новых карт добавлены в конец `map_index` (существующие индексы не сдвинуты).

## Что проверять (на кластере)
1. **Все добавленные варпы** в `npc/warps/backport/**` срабатывают и ведут в верную точку.
2. **Существующие варпы не сломаны** — выборочно классические переходы (поля Morroc/Prontera, anthell
   из `moc_fild04`) ведут туда же, что и раньше.
3. **Конфликты из `doc/backport_warp_conflicts.md`**: пройти каждую запись ВХОД/ВЫХОД, вместо `решение?`
   вписать корректирующие данные (поставить вход по координатам / сменить выход / удалить варп / и т.п.).
   Особое внимание — `moc_fild20` (Сограт, новый вид) и другие перечисленные карты.
4. Новые карты без `.gat` у клиента — отметить для деплоя GRF.

## Как воспроизвести генерацию
`python3 dumps/forge/backport-warps.py` (идемпотентно). Проверки: `--selftest`, `--verify`.
Правила слияния — `doc/backport_prerenewal_maps_warps_design.md`.
```

- [ ] **Step 2: Fill in the real [N]/[M] counts**

Run: `python3 dumps/forge/backport-warps.py --dry-run`
Replace `[N]` (register maps) and `[M]` (added warps) in the document with the reported numbers.

- [ ] **Step 3: Commit the tester document**

```bash
git add doc/backport_maps_warps_changes.md
git commit -m "doc: tester checklist for pre-renewal maps/warps backport

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Push

- [ ] **Step 1: Push the backport series to origin/x64**

Run: `git push origin x64`
Expected: the five commits (generator, generated artifacts, wiring, [optional fix], tester doc) land on `origin/x64`.

---

## Notes for the implementer
- `EA_ROOT` defaults to `/tmp/eathena-ref`; override via env if the reference moves.
- The generator only reads `warp`-type portals from `npc/warps/**`; quest-gated NPC warps (renewal-town
  entrances) are intentionally out of scope and handled by the later NPC port.
- Re-running the generator is safe: backport files and docs are overwritten; the two appends are guarded.
- This plan's scope is **locations + warps only**. Mobs, items, and town NPCs are separate tasks.

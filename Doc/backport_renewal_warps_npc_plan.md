# Renewal warps + town-NPC backport — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make 6 already-registered renewal zones (Dewata, El Dicastes, Eclage, Malangdo, Malaya, Mora/Bifrost) functional by backporting their static warps and town-NPCs from rAthena into uAthena, adapting rAthena-only script syntax to uAthena's older engine.

**Architecture:** Two idempotent Python build-time generators under `dumps/forge/`, modeled on the existing `backport-warps.py` / `backport-town-npcs.py` / `backport-renewal-cards.py`. Generator 1 emits static warps (`warp2`→`warp`, additive merge rule); Generator 2 emits town-NPCs (entity parse + dynamic token-gap sanitizer + per-group adaptation + Kafra→`duplicate(kaf_alberta)`). Output is isolated under `npc/warps/backport/re/` and `npc/backport/re_cities/`, wired via append-only include blocks. No engine (`.c`) changes.

**Tech Stack:** Python 3 (stdlib only), uAthena C map-server (boot-parse verification), rAthena reference at `/tmp/rathena-ref` (sparse-checkout, commit `7f08087`).

## Global Constraints

- **Source pinned:** rAthena commit `7f080871c8b3bbe7a79027194633201c63422ee1` (2026-06-18) at `/tmp/rathena-ref`. `npc/re/` is materialized via sparse-checkout (done in Task 1 setup).
- **No engine changes.** Data + isolated NPC scripts only. uAthena script engine is the older fork (no `.@`? — it HAS `.@`; no `warp2`; no `getnpcid`; buildins=330 vs rAthena 671).
- **Additive + isolated.** Output ONLY under `npc/warps/backport/re/` and `npc/backport/re_cities/`. Existing files and `map_index.txt` order are never modified. Includes are append-only blocks in `npc/scripts_warps.conf` / `npc/scripts_athena.conf`.
- **Generators write UTF-8.** Warp/NPC bodies are ASCII; conflict/gap docs carry Cyrillic. NEVER open existing cp1251 (`Non-ISO`) `npc/` files with an editor that re-encodes.
- **All docs → `Doc/`** (capital D), never `doc/`.
- **Before every push:** `git fetch && git rebase` (Cline Bot `<bot@pechsoft.com>` pushes `x64` concurrently).
- **Commit message footer:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Shell has `set -e`+`pipefail`:** wrap `grep`/`pgrep`/`pkill` that may exit non-zero in `set +e`; never `pgrep -f` a string matching your own cmdline (use `pgrep -x`).
- **Design reference:** `Doc/backport_renewal_warps_npc_design.md` (scope, merge rule, measured gap, adaptation groups).

**Measured facts (verified, not estimated):** 149 static warps (`warp2`=0); ~20 script + 16 duplicate + 1 function inside warp-files (transport: Dicastes elevators, Mora Small Holes, Malaya jeepney); 156 script + 33 duplicate town-NPCs (4555 lines); scope kafras live in `npc/re/kafras/kafras.txt` (`kaf_dewata`, `kaf_malaya1/2`, …); command-gap = 15 buildins (mostly ≤3 uses), `consumeitem`(6)+`getnpcid`(24) the notable ones; all scope maps already in `map_index` (0 additions).

---

## File Structure

**Created:**
- `dumps/forge/backport-renewal-warps.py` — Generator 1 (static warps). Responsibility: parse rAthena scope warps, apply merge rule, emit isolated warp files + conflict doc + includes + endpoint-completeness check.
- `dumps/forge/backport-renewal-town-npcs.py` — Generator 2 (town-NPCs). Responsibility: parse NPC entities from town/warp/kafra files, sanitize+adapt rAthena-only tokens, emit isolated NPC files + gap log + includes.
- `npc/warps/backport/re/**/*.txt` — Generator 1 output (warps).
- `npc/backport/re_cities/*.txt` — Generator 2 output (town-NPCs + extracted kafras).
- `Doc/backport_renewal_warp_conflicts.md` — Generator 1 conflict log (testers fill `решение?`).
- `Doc/backport_renewal_npc_gap.md` — Generator 2 gap log (adapted/commented commands).
- `Doc/backport_renewal_warps_npc_changes.md` — final change summary.
- `dumps/forge/backport-renewal-warps-includes.txt`, `dumps/forge/backport-renewal-npc-includes.txt` — generated include lines.

**Modified (append-only):**
- `npc/scripts_warps.conf` — add renewal-warps include block.
- `npc/scripts_athena.conf` — add renewal-NPC include block.

---

## Task 1: Static warps generator (R1 endpoint-check + R2 warps)

**Files:**
- Create: `dumps/forge/backport-renewal-warps.py`
- Create (generated): `npc/warps/backport/re/**`, `Doc/backport_renewal_warp_conflicts.md`, `dumps/forge/backport-renewal-warps-includes.txt`
- Modify: `npc/scripts_warps.conf`

**Interfaces:**
- Produces: isolated warp files under `npc/warps/backport/re/`; the include block in `scripts_warps.conf`. Endpoint-completeness (`unreg`) must be empty (folds in R1 location verification).

- [ ] **Step 1: Materialize rAthena `npc/re/` (source setup)**

```bash
cd /tmp/rathena-ref && git sparse-checkout add npc/re && \
  test -f npc/re/warps/cities/malaya.txt && echo "SETUP OK"
```
Expected: `SETUP OK` (files on disk). (Already done in design phase; re-run is idempotent.)

- [ ] **Step 2: Write the generator with selftest fixtures (test-first)**

Create `dumps/forge/backport-renewal-warps.py`:

```python
#!/usr/bin/env python3
"""Additive renewal warps backport: rathena-ref -> uAthena (6 registered zones).

Emits (repo root):
  npc/warps/backport/re/<subtree>/<file>.txt        new warps (warp2 normalized to warp)
  Doc/backport_renewal_warp_conflicts.md            ВХОД/ВЫХОД rejected points (testers fill)
  dumps/forge/backport-renewal-warps-includes.txt   scripts_warps.conf lines

Modes: --selftest | --dry-run | --verify | (default) generate. Idempotent. Run from repo root.
See Doc/backport_renewal_warps_npc_design.md.
"""
import os, re, sys, glob
from collections import Counter

UA_ROOT = os.environ.get("UA_ROOT", ".")
RA_ROOT = os.environ.get("RA_ROOT", "/tmp/rathena-ref")

# Renewal zones already registered in uAthena db/map_index.txt (design §3).
SCOPE_PREFIXES = ("dewata", "dew_", "dicastes", "dic_", "eclage", "ecl_",
                  "malangdo", "mal_", "malaya", "ma_fild", "ma_in", "ma_dun",
                  "ma_scene", "ma_zif", "mora", "bif_fild")

def in_scope(m):
    return m.startswith(SCOPE_PREFIXES)

def parse_warp(line):
    """src(map,x,y[,dir]) <ws> warp|warp2 <ws> name <ws> xs,ys,dstmap,dx,dy -> dict|None.
    warp2 (invisible) is normalized to warp (uAthena engine has no warp2)."""
    s = line.strip()
    if not s or s.startswith("//"):
        return None
    p = re.split(r'[\t ]+', s)
    if len(p) < 4 or p[1] not in ("warp", "warp2"):
        return None
    src = p[0].split(","); rhs = p[3].split(",")
    if len(src) < 3 or len(rhs) < 5:
        return None
    try:
        x, y = int(src[1]), int(src[2]); dx, dy = int(rhs[3]), int(rhs[4])
    except ValueError:
        return None
    return {"srcmap": src[0], "x": x, "y": y, "facing": src[3] if len(src) > 3 else "0",
            "name": p[2], "xs": rhs[0], "ys": rhs[1], "dstmap": rhs[2], "dx": dx, "dy": dy,
            "warp2": p[1] == "warp2"}

def load_warps(root, subtree, skip_renewal_out=False):
    out = []
    for path in glob.glob(os.path.join(root, subtree, "**", "*.txt"), recursive=True):
        if skip_renewal_out and "/backport/re/" in path.replace("\\", "/"):
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

def classify(ua_warps, ra_warps, ua_maps):
    ua_names, ua_tiles = {}, {}
    for w in ua_warps:
        ua_names.setdefault(w["name"], w)
        ua_tiles.setdefault((w["srcmap"], w["x"], w["y"]), w)
    added, conflicts, unreg, boundary = {}, {}, set(), []
    for w in ra_warps:
        s, d = w["srcmap"], w["dstmap"]
        if not (in_scope(s) or in_scope(d)):
            continue
        hit = ua_names.get(w["name"]) or ua_tiles.get((s, w["x"], w["y"]))
        if hit:
            ref = (f'{hit["name"]}: {hit["srcmap"]},{hit["x"]},{hit["y"]}'
                   f'->{hit["dstmap"]},{hit["dx"]},{hit["dy"]}')
            head = f'{s},{w["x"]},{w["y"]} -> {d},{w["dx"]},{w["dy"]}'
            if in_scope(d):
                conflicts.setdefault(d, {"vhod": [], "vyhod": []})["vhod"].append(
                    f'{head} | СОХРАНЁН {ref} | решение?')
            else:
                conflicts.setdefault(s, {"vhod": [], "vyhod": []})["vyhod"].append(
                    f'{head} | конфликт со старым {ref} | решение?')
            continue
        # Endpoint completeness (folds in R1). An unregistered endpoint that is itself a
        # scope map = a real R1 gap (abort: a scope zone is missing from map_index). An
        # unregistered endpoint OUTSIDE scope = an out-of-scope boundary (e.g. the
        # dimensional-gap hub 'dali'): per design §3 "0 new maps" -> skip the warp + log it.
        bad = [m for m in (s, d) if m not in ua_maps]
        if bad:
            real = [m for m in bad if in_scope(m)]
            if real:
                unreg.update(real)
            else:
                boundary.append(f'{s},{w["x"]},{w["y"]} -> {d} ({w["name"]}) | '
                                f'unregistered out-of-scope endpoint {bad} | SKIPPED')
            continue                          # never emit a warp with an unregistered endpoint
        rel = os.path.relpath(w["file"],
                              os.path.join(RA_ROOT, "npc", "re", "warps")).replace("\\", "/")
        added.setdefault(rel, []).append(
            f'{s},{w["x"]},{w["y"]},{w["facing"]}\twarp\t{w["name"]}\t'
            f'{w["xs"]},{w["ys"]},{d},{w["dx"]},{w["dy"]}')
    return added, conflicts, sorted(unreg), boundary

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def emit(added, conflicts, unreg, boundary):
    includes = []
    for rel in sorted(added):
        lines = sorted(set(added[rel]))
        hdr = ("//===== uAthena backport (renewal warps, GENERATED) =========\n"
               "//= Additive renewal warps from rathena-ref (warp2->warp).\n"
               "//= DO NOT EDIT - regenerate via dumps/forge/backport-renewal-warps.py\n"
               f"//= Source: npc/re/warps/{rel}\n"
               "//============================================================\n")
        write_file(os.path.join(UA_ROOT, "npc", "warps", "backport", "re", rel),
                   hdr + "\n".join(lines) + "\n")
        includes.append(f"npc: npc/warps/backport/re/{rel}")
    buf = ["# Конфликты renewal-варпов бэкпорта (отвергнутые точки)\n\n",
           "Тестировщики: замените `решение?` корректирующими данными.\n",
           "Схема — Doc/backport_renewal_warps_npc_design.md §4.2.\n"]
    for m in sorted(conflicts):
        c = conflicts[m]
        buf.append(f"\n## {m}\n")
        buf.append("# ВХОД: требуемая(карта,x,y) -> на_новой(карта,x,y) | СОХРАНЁН старый | решение?\n")
        buf += [e + "\n" for e in sorted(set(c["vhod"]))]
        buf.append("# ВЫХОД: на_новой(карта,x,y) -> на_старой(карта,x,y) | примечание | решение?\n")
        buf += [e + "\n" for e in sorted(set(c["vyhod"]))]
    if boundary:
        buf.append("\n## Пропущенные boundary-варпы (незарегистрированный endpoint вне scope)\n")
        buf.append("# Концепция «0 новых карт» (§3): варп в карту вне 6 зон, которой нет в\n")
        buf.append("# map_index (напр. dimensional-gap хаб 'dali'), пропущен. решение?\n")
        buf += [e + "\n" for e in sorted(set(boundary))]
    write_file(os.path.join(UA_ROOT, "Doc", "backport_renewal_warp_conflicts.md"), "".join(buf))
    write_file(os.path.join(UA_ROOT, "dumps", "forge", "backport-renewal-warps-includes.txt"),
               "\n".join(includes) + "\n")

def report(added, conflicts, unreg, boundary):
    na = sum(len(v) for v in added.values())
    nv = sum(len(c["vhod"]) for c in conflicts.values())
    nx = sum(len(c["vyhod"]) for c in conflicts.values())
    print(f"added warps: {na} in {len(added)} files | VHOD: {nv} | VYHOD: {nx} | "
          f"conflict maps: {len(conflicts)} | boundary-skipped: {len(boundary)} | "
          f"REAL unregistered scope endpoints: {unreg or 'none'}")

def real_data():
    ua = load_warps(UA_ROOT, "npc", skip_renewal_out=True)
    ra = load_warps(RA_ROOT, os.path.join("npc", "re", "warps"))
    ua_maps = load_mapindex(os.path.join(UA_ROOT, "db", "map_index.txt"))
    return classify(ua, ra, ua_maps)

def selftest():
    ra_root_warps = os.path.join(RA_ROOT, "npc", "re", "warps", "cities", "dewata.txt")
    def mk(line):
        w = parse_warp(line); w["file"] = ra_root_warps; return w
    # warp2 normalization
    w2 = parse_warp("dewata,1,1,0\twarp2\tinvis\t1,1,dew_fild01,5,5")
    assert w2 and w2["warp2"] is True, w2
    ua_maps = {"dewata", "dew_fild01", "malaya", "ma_fild01"}
    ua = [mk("dewata,100,100,0\twarp\tdew_keep\t1,1,dew_fild01,5,5")]
    ra = [mk("dewata,100,100,0\twarp\tdew_keep\t1,1,dew_fild01,9,9"),   # tile collision -> conflict
          mk("malaya,50,50,0\twarp\tma_new\t1,1,ma_fild01,5,5"),         # new -> added
          mk("dewata,77,77,0\twarp\tto_hub\t1,1,dali,5,5"),              # out-of-scope endpoint -> boundary skip
          mk("dewata,88,88,0\twarp\tto_ecl\t1,1,ecl_in01,5,5"),          # scope endpoint missing from map_index -> REAL unreg
          mk("prontera,1,1,0\twarp\tnope\t1,1,prontera,2,2")]            # out of scope -> skipped
    added, conflicts, unreg, boundary = classify(ua, ra, ua_maps)
    assert sum(len(v) for v in added.values()) == 1, added
    # dew_keep collides; both ends in scope -> keyed by dst (in_scope(d) branch = ВХОД)
    assert len(conflicts["dew_fild01"]["vhod"]) == 1, conflicts
    assert unreg == ["ecl_in01"], unreg          # scope map -> real R1 gap
    assert len(boundary) == 1 and "dali" in boundary[0], boundary  # out-of-scope hub -> skipped
    # added line normalizes warp2 to "warp"
    aline = next(iter(added.values()))[0]
    assert "\twarp\t" in aline and "warp2" not in aline, aline
    print("SELFTEST OK")

def verify():
    allw = load_warps(UA_ROOT, "npc")
    bp = [w for w in allw if "/backport/re/" in w["file"].replace("\\", "/")]
    other = [w for w in allw if "/backport/re/" not in w["file"].replace("\\", "/")]
    other_names = Counter(w["name"] for w in other)
    bp_names = Counter(w["name"] for w in bp)
    other_tiles = {(w["srcmap"], w["x"], w["y"]) for w in other}
    ua_maps = load_mapindex(os.path.join(UA_ROOT, "db", "map_index.txt"))
    bad_names = [(n, k, other_names.get(n, 0)) for n, k in bp_names.items()
                 if k > 1 or other_names.get(n, 0) > 0]
    bad_tiles = [w for w in bp if (w["srcmap"], w["x"], w["y"]) in other_tiles]
    bad_ends = sorted({m for w in bp for m in (w["srcmap"], w["dstmap"]) if m not in ua_maps})
    print(f"renewal backport warps: {len(bp)} | dup-name: {len(bad_names)} | "
          f"tile-collision: {len(bad_tiles)} | unregistered-endpoints: {bad_ends or 'none'}")
    for b in bad_names[:50]: print("   DUPNAME", b)
    for w in bad_tiles[:50]: print("   TILE", w["srcmap"], w["x"], w["y"], w["name"])
    ok = not bad_names and not bad_tiles and not bad_ends
    print("VERIFY", "OK" if ok else "FAILED")
    return ok

def main():
    if "--selftest" in sys.argv:
        selftest(); return
    if "--verify" in sys.argv:
        sys.exit(0 if verify() else 1)
    added, conflicts, unreg, boundary = real_data()
    report(added, conflicts, unreg, boundary)
    if unreg and "--dry-run" not in sys.argv:
        print("ABORT: scope map(s) missing from map_index (R1 incomplete):", unreg); sys.exit(2)
    if "--dry-run" not in sys.argv:
        emit(added, conflicts, unreg, boundary)
        print("written.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the selftest, verify it passes**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-warps.py --selftest`
Expected: `SELFTEST OK`

- [ ] **Step 4: Dry-run against real data, confirm 0 REAL unregistered endpoints**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-warps.py --dry-run`
Expected (verified during planning): `added warps: 139 in 10 files | VHOD: 0 | VYHOD: 0 | conflict maps: 0 | boundary-skipped: 2 | REAL unregistered scope endpoints: none`
- `boundary-skipped: 2` = the dimensional-gap hub warps `dali->bif_fild01` / `dali->dic_fild02` (out-of-scope endpoint `dali` not in map_index; skipped per design §3 "0 new maps", logged to the conflict doc). Expected and correct.
- If `REAL unregistered scope endpoints` is non-empty: STOP — a scope zone is genuinely missing from `db/map_index.txt`; append it (at file end, never shift indices), document, re-run. (None expected.)

- [ ] **Step 5: Generate**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-warps.py`
Expected: report line + `written.`. Inspect `git status` — new files only under `npc/warps/backport/re/`, `Doc/backport_renewal_warp_conflicts.md`, `dumps/forge/backport-renewal-warps-includes.txt`.

- [ ] **Step 6: Run static verify**

Run: `cd /root/uAthena && UA_ROOT=. python3 dumps/forge/backport-renewal-warps.py --verify`
Expected: `VERIFY OK` (0 dup-name, 0 tile-collision, 0 unregistered-endpoints).

- [ ] **Step 7: Wire the include block (append-only)**

Append the generated lines from `dumps/forge/backport-renewal-warps-includes.txt` to `npc/scripts_warps.conf` under a new block. Open `npc/scripts_warps.conf`, and at the END add:

```
// ===== Backport renewal warps (GENERATED) =====
// (paste the contents of dumps/forge/backport-renewal-warps-includes.txt below)
```
followed by every `npc: npc/warps/backport/re/...` line. Use a plain append (the file is ASCII):
```bash
cd /root/uAthena && { echo ""; echo "// ===== Backport renewal warps (GENERATED) ====="; cat dumps/forge/backport-renewal-warps-includes.txt; } >> npc/scripts_warps.conf
```
Verify: `tail -20 npc/scripts_warps.conf` shows the block.

- [ ] **Step 8: Boot-parse verification (local map-server)**

Boot the map-server locally per the local-cluster-boot-test method (char_ip/map_ip=127.0.0.1, GRF symlink, local MariaDB) and grep the log for script errors on the new warp files.
Run (after `make sql` build + local cluster up):
```bash
cd /root/uAthena && set +e; ./map-server_sql 2>&1 | tee /tmp/r2_boot.log | grep -iE "script error|error.*backport/re|warp.*not found" ; set -e
grep -c "backport/re" /tmp/r2_boot.log
```
Expected: 0 script errors referencing `backport/re`; server reaches "Server is ready". (`.gat not found` warnings for ALL maps are expected on the dev box — unrelated, per design §5.)

- [ ] **Step 9: Commit**

```bash
cd /root/uAthena && git fetch && git rebase
git add dumps/forge/backport-renewal-warps.py npc/warps/backport/re/ \
        Doc/backport_renewal_warp_conflicts.md dumps/forge/backport-renewal-warps-includes.txt \
        npc/scripts_warps.conf
git commit -m "$(cat <<'EOF'
backport: renewal static warps (6 zones) -> npc/warps/backport/re/ [renewal-warps]

Generator dumps/forge/backport-renewal-warps.py (warp2->warp, additive merge,
endpoint-completeness). 0 engine changes. Conflicts -> Doc/. Verified static.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Town-NPC generator core (parse + sanitizer + adaptation + kafra)

**Files:**
- Create: `dumps/forge/backport-renewal-town-npcs.py`

**Interfaces:**
- Consumes: rAthena `npc/re/cities/<zone>.txt`, scope warp files (non-warp entities), `npc/re/kafras/kafras.txt` (scope kafras). uAthena `db/const.txt`, `src/map/script.c`, `db/skill_db.txt` for the KNOWN-token set.
- Produces: `gen()` writing `npc/backport/re_cities/*.txt` + gap log + includes; `adapt_text(text) -> (new_text, gap_events)`; `kafra_lines()`; `verify()`. Task 3 runs these.

- [ ] **Step 1: Write the generator with selftest fixtures (test-first)**

Create `dumps/forge/backport-renewal-town-npcs.py`:

```python
#!/usr/bin/env python3
"""Renewal town-NPC backport: rathena-ref -> uAthena (6 zones). 0 engine changes.

Input  = npc/re/cities/<zone>.txt (whole)
       + non-warp entries (script/function/duplicate) from scope warp files
       + scope kafra NPCs from npc/re/kafras/kafras.txt
Adapt rAthena-only script tokens to uAthena's older engine (design §4.3):
  - consumeitem <id>;            -> delitem <id>,1;            (group B, real transform)
  - any other gap buildin / ET_* -> statement commented + logged (group A no-op / C drop)
    (gap buildin set computed dynamically = rAthena buildins - uAthena buildins,
     minus 'duplicate' which is an engine NPC construct uAthena supports)
Kafra (scope maps) -> duplicate(kaf_alberta), preserving map/coords/sprite/name.
Outputs: npc/backport/re_cities/<zone>.txt
       + Doc/backport_renewal_npc_gap.md
       + dumps/forge/backport-renewal-npc-includes.txt
Modes: --selftest | --verify | (default) generate. Run from repo root.
See Doc/backport_renewal_warps_npc_design.md.
"""
import os, re, sys, glob
from collections import Counter

UA_ROOT = os.environ.get("UA_ROOT", ".")
RA_ROOT = os.environ.get("RA_ROOT", "/tmp/rathena-ref")
OUT_DIR = os.path.join("npc", "backport", "re_cities")
KAFRA_BASE = "kaf_alberta"

ZONES = ["dewata", "dicastes", "eclage", "malangdo", "malaya", "mora"]
SCOPE_MAP_PREFIXES = ("dewata", "dew_", "dicastes", "dic_", "eclage", "ecl_",
                      "malangdo", "mal_", "malaya", "ma_fild", "ma_in", "ma_dun",
                      "ma_scene", "ma_zif", "mora", "bif_fild")

HEADER = ("//===== uAthena backport (renewal town-NPCs, GENERATED) ======\n"
          "//= Port from rathena-ref; rAthena-only tokens adapted/commented.\n"
          "//= DO NOT EDIT - regenerate via dumps/forge/backport-renewal-town-npcs.py\n"
          "//= Source: {src}\n"
          "//============================================================\n")

def read(p):
    with open(p, encoding="latin-1") as f:
        return f.read()

def write(p, s):                        # UTF-8: gap/changes docs carry Cyrillic
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

def write_raw(p, s):                     # latin-1: byte-preserving for NPC scripts whose
    os.makedirs(os.path.dirname(p), exist_ok=True)   # dialogue carries 8-bit (EUC-KR) bytes;
    with open(p, "w", encoding="latin-1") as f:      # the server reads scripts as raw bytes,
        f.write(s)                                   # so re-encoding to UTF-8 would corrupt them

# ---- uAthena known-token sets (for dynamic gap) -------------------------------
def load_consts():
    c = set()
    for ln in read(os.path.join(UA_ROOT, "db", "const.txt")).splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("//"):
            c.add(ln.split()[0].upper())
    return c

def load_buildins(path):
    txt = read(path); b = set()
    for m in re.finditer(r'BUILDIN_DEF\(\s*(\w+)', txt):
        b.add(m.group(1).upper())
    for m in re.finditer(r'BUILDIN_DEF2\(\s*\w+\s*,\s*"([^"]+)"', txt):
        b.add(m.group(1).upper())
    return b

UA_BUILTINS = load_buildins(os.path.join(UA_ROOT, "src", "map", "script.c"))
RA_BUILTINS = load_buildins(os.path.join(RA_ROOT, "src", "map", "script.cpp"))
# 'duplicate' is an engine NPC construct (npc.c), not a script buildin -> never a gap.
GAP_BUILTINS = (RA_BUILTINS - UA_BUILTINS) - {"DUPLICATE"}

# Site-specific fixes for non-generalizable rAthena-only TRANSPORT patterns. Applied
# verbatim (substring replace) after consumeitem, before generic gap-commenting; each
# logged as SITEFIX. Keeps regeneration deterministic (vs hand-editing generated files).
SITE_FIXES = [
    # F_Malaya_Jeepney loop: getargcount() (absent in uAthena) -> getarg sentinel.
    # uAthena getarg is "i?": getarg(n, default) returns default when arg n is absent.
    ('.@i < getargcount()', 'getarg(.@i, "\\x7F") != "\\x7F"'),
    # Small Hole (bifrost_field0000) Mora<->Bifrost transport: charat()/strnpcinfo
    # index (uAthena has no charat) -> compare()-based index from unique-name suffix.
    ('switch(atoi(charat(strnpcinfo(2),9))) {',
     'set .@holeIdx, compare(strnpcinfo(2),"mora1")?1:'
     'compare(strnpcinfo(2),"mora2")?2:compare(strnpcinfo(2),"mora3")?3:0;\n'
     '\t\tswitch(.@holeIdx) {'),
]

def load_mapindex():
    s = set()
    for ln in read(os.path.join(UA_ROOT, "db", "map_index.txt")).splitlines():
        t = ln.strip()
        if t and not t.startswith("//"):
            s.add(t.split()[0])
    return s

UA_MAPS = load_mapindex()  # for boundary-skip of NPCs on out-of-scope unregistered maps

# ---- adaptation ---------------------------------------------------------------
def code_only(line):
    """Strip string literals so gap detection ignores dialogue text & skill-name
    args: a gap WORD inside mes "...cooking..." is prose, not the cooking buildin."""
    return re.sub(r'"[^"]*"', ' ', line)

def adapt_text(text):
    """Return (new_text, events). events = list of (kind, token, line) for the gap log."""
    events = []
    out = []
    for raw in text.splitlines():
        line = raw
        stripped = line.strip()
        if stripped.startswith("//"):
            out.append(line); continue
        # NPC placed on a map absent from map_index (out-of-scope, e.g. izlude_* academy
        # duplicates of an in-scope base) -> comment + log (mirrors warp boundary-skip).
        df = re.match(r'^([A-Za-z0-9_]+),\d+,\d+', line)
        if df and df.group(1) not in UA_MAPS:
            indent = line[:len(line) - len(line.lstrip())]
            if "{" in line:                       # multi-line script on unregistered map
                events.append(("MANUAL", "unregistered-map:" + df.group(1), stripped))
                out.append(line)
            else:                                 # single-line (duplicate/shop) -> comment
                out.append(f"{indent}//[BACKPORT-BOUNDARY:{df.group(1)}] {stripped}")
                events.append(("BOUNDARY", df.group(1), stripped))
            continue
        # group B: consumeitem <id>; -> delitem <id>,1;
        m = re.search(r'\bconsumeitem\s+(\d+)\s*;', line)
        if m:
            line = re.sub(r'\bconsumeitem\s+(\d+)\s*;', r'delitem \1,1;', line)
            events.append(("ADAPT", "consumeitem->delitem", stripped))
            out.append(line); continue
        # site-specific transport fixes (non-generalizable). Modify in place (no continue)
        # so the line still flows through the generic CLASS B/D/A syntax transforms below
        # (e.g. the jeepney loop needs both the getargcount site-fix AND CLASS D for/++).
        for old, new in SITE_FIXES:
            if old in line:
                line = line.replace(old, new)
                events.append(("SITEFIX", old.split("(")[0].strip(), stripped))
        # CLASS B: rAthena self-target empty-paren (en|dis)ablenpc()/(hideon|hideoff)npc()
        # — uAthena needs the NPC name "s" -> ...npc strnpcinfo(0)
        if re.search(r'\b(enable|disable|hideon|hideoff)npc\(\)', line):
            line = re.sub(r'\b(enable|disable|hideon|hideoff)npc\(\)',
                          r'\1npc strnpcinfo(0)', line)
            events.append(("ADAPT", "npc()->npc strnpcinfo(0)", stripped))
        # CLASS D: rAthena for-init '=' and '++/--' increments (uAthena for uses the
        # 'set var,N' / 'set var,var+1' idiom; the parser has no '=' init or '++'). The
        # required '.@var' anchor before ++/-- skips prose like mes "Snort--" / "--- ".
        before_d = line
        line = re.sub(r'for\s*\(\s*(\.@\w+)\s*=\s*([^;]+);', r'for (set \1,\2;', line)
        line = re.sub(r'(\.@\w+)\+\+', r'set \1,\1+1', line)
        line = re.sub(r'(\.@\w+)--', r'set \1,\1-1', line)
        if line != before_d:
            events.append(("ADAPT", "for/incr->set", before_d.strip()))
        # CLASS A: rAthena '=' assignment -> uAthena 'set var, expr' (old parser has no
        # '=' assignment). Single '=' only (the [^=] guard skips ==, the \.@? anchor and
        # leading-var match skip +=,<=,>=,!= and mid-expression equals).
        ma = re.match(r'^(\s*)(\.@?\w+\$?(?:\[[^\]]*\])?)\s*=\s*([^=].*?);\s*$', line)
        if ma:
            line = f'{ma.group(1)}set {ma.group(2)}, {ma.group(3)};'
            events.append(("ADAPT", "=->set", stripped))
        # detect remaining gap buildins + ET_* emotion consts (over code only, NOT
        # inside string literals: a gap word in mes/dialogue text is prose, not a call)
        code = code_only(line)
        idents = set(t.upper() for t in re.findall(r'[A-Za-z_]\w*', code))
        gap_hit = sorted((idents & GAP_BUILTINS))
        et_hit = re.findall(r'\bET_[A-Z_]+\b', code)
        if gap_hit or et_hit:
            tok = ",".join([g.lower() for g in gap_hit] + et_hit)
            if "{" in line or "}" in line:
                # commenting would unbalance braces -> leave for manual review
                events.append(("MANUAL", tok, stripped))
                out.append(line)
            else:
                indent = line[:len(line) - len(line.lstrip())]
                out.append(f"{indent}//[BACKPORT-GAP:{tok}] {stripped}")
                events.append(("COMMENT", tok, stripped))
            continue
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), events

# ---- structural extraction ----------------------------------------------------
def non_warp(text):
    """Drop only top-level static-warp definition lines (single-line); keep script/
    function/duplicate blocks (their bodies have no field[1]=='warp')."""
    keep = []
    for ln in text.splitlines():
        f = ln.split("\t")
        if len(f) >= 2 and f[1] == "warp":
            continue
        keep.append(ln)
    return "\n".join(keep)

def def_lines(text):
    for line in text.splitlines():
        s = line.rstrip("\n"); t = s.strip()
        if not t or t.startswith("//"):
            continue
        f = s.split("\t")
        if len(f) >= 3 and "," in f[0]:
            yield s, f

def in_scope_map(m):
    return m.startswith(SCOPE_MAP_PREFIXES)

def normalize_kafra_name(name):
    if "::" in name:
        base, label = name.split("::", 1)
        return base + "#" + label
    return name

def kafra_lines():
    """Scope kafra NPCs from npc/re/kafras/kafras.txt -> duplicate(kaf_alberta)."""
    out = []
    src = os.path.join(RA_ROOT, "npc", "re", "kafras", "kafras.txt")
    if not os.path.exists(src):
        return out
    for s, f in def_lines(read(src)):
        loc = f[0].split(",")[0]
        if not in_scope_map(loc):
            continue
        if f[1] != "script" or "kafra" not in f[2].lower():
            continue
        sprite = f[3].split(",")[0].split("{")[0].strip()
        name = normalize_kafra_name(f[2])
        out.append(f"{f[0]}\tduplicate({KAFRA_BASE})\t{name}\t{sprite}")
    return out

# ---- generate -----------------------------------------------------------------
def scope_warp_files():
    out = []
    for sub in ("cities", "fields", "dungeons"):
        for p in sorted(glob.glob(os.path.join(RA_ROOT, "npc", "re", "warps", sub, "*.txt"))):
            base = os.path.basename(p)
            if any(z in base for z in ("dewata", "dicastes", "eclage", "malangdo", "malaya",
                                       "bif_fild", "dic_fild", "dic_dun", "ecl_dun", "ecl_tdun")):
                out.append(p)
    return out

def collect_used_scope_maps():
    """Scope maps actually referenced by the backport warps (src+dst) and town-NPC
    placements. These must be in conf/maps_athena.conf for the server to LOAD the map
    (map_index only assigns the ID; the load-list is maps_athena.conf). Maps still need
    a .gat in the GRF at deploy time, else the server drops them ('Removing map')."""
    scope_mi = {m for m in UA_MAPS if m.startswith(SCOPE_MAP_PREFIXES)}
    used = set()
    for p in glob.glob(os.path.join(UA_ROOT, "npc", "warps", "backport", "re", "**", "*.txt"),
                       recursive=True):
        for ln in read(p).splitlines():
            if ln.startswith("//") or "\twarp\t" not in ln:
                continue
            c = ln.split("\t"); used.add(c[0].split(",")[0])
            rhs = c[3].split(",")
            if len(rhs) >= 3:
                used.add(rhs[2])
    for p in glob.glob(os.path.join(UA_ROOT, OUT_DIR, "*.txt")):
        for ln in read(p).splitlines():
            s = ln.strip()
            if not s or s.startswith("//") or s.startswith("function"):
                continue
            c = ln.split("\t")
            if "," in c[0] and not c[0].startswith("-"):
                used.add(c[0].split(",")[0])
    return sorted(used & scope_mi)

def gen():
    gap_buf = ["# Renewal town-NPC gap-лог (адаптации/комментирования)\n\n",
               "Тестировщики: проверьте COMMENT/MANUAL — потерянная функция или ручная правка.\n",
               "Схема — Doc/backport_renewal_warps_npc_design.md §4.3.\n"]
    includes = []
    total_ev = Counter()
    # per-zone town file + that zone's non-warp warp content
    warp_by_zone = {}
    for p in scope_warp_files():
        b = os.path.basename(p)
        z = next((z for z in ZONES if z[:3] in b or z in b), None)
        # map warp-file basenames to a zone bucket
        if "dewata" in b: z = "dewata"
        elif "dicastes" in b or b.startswith("dic_"): z = "dicastes"
        elif "eclage" in b or b.startswith("ecl_"): z = "eclage"
        elif "malangdo" in b: z = "malangdo"
        elif "malaya" in b: z = "malaya"
        elif "bif_fild" in b: z = "mora"
        if z:
            warp_by_zone.setdefault(z, []).append(p)
    for zone in ZONES:
        town = os.path.join(RA_ROOT, "npc", "re", "cities", zone + ".txt")
        parts = []
        srcs = []
        if os.path.exists(town):
            parts.append(read(town)); srcs.append(f"npc/re/cities/{zone}.txt")
        for wp in warp_by_zone.get(zone, []):
            parts.append(non_warp(read(wp)))
            srcs.append("npc/re/warps/.../" + os.path.basename(wp) + " (non-warp)")
        body = "\n".join(parts)
        new_body, events = adapt_text(body)
        out_path = os.path.join(UA_ROOT, OUT_DIR, zone + ".txt")
        write_raw(out_path, HEADER.format(src=", ".join(srcs)) + new_body +
                  ("" if new_body.endswith("\n") else "\n"))
        includes.append(f"npc: npc/backport/re_cities/{zone}.txt")
        gap_buf.append(f"\n## {zone}\n")
        for kind, tok, ln in events:
            total_ev[kind] += 1
            gap_buf.append(f"- {kind} [{tok}] {ln}\n")
    # kafras (all scope zones) -> one file
    kaf = kafra_lines()
    if kaf:
        write_raw(os.path.join(UA_ROOT, OUT_DIR, "kafras.txt"),
                  HEADER.format(src="npc/re/kafras/kafras.txt (scope, adapted to " + KAFRA_BASE + ")")
                  + "\n".join(kaf) + "\n")
        includes.append("npc: npc/backport/re_cities/kafras.txt")
    write(os.path.join(UA_ROOT, "Doc", "backport_renewal_npc_gap.md"), "".join(gap_buf))
    write(os.path.join(UA_ROOT, "dumps", "forge", "backport-renewal-npc-includes.txt"),
          "\n".join(includes) + "\n")
    used_maps = collect_used_scope_maps()
    write(os.path.join(UA_ROOT, "dumps", "forge", "backport-renewal-maps-athena.txt"),
          "\n".join("map: " + m for m in used_maps) + "\n")
    print(f"zones: {len(ZONES)} | kafra duplicates: {len(kaf)} | "
          f"gap events: {dict(total_ev)} | gap buildins known: {len(GAP_BUILTINS)} | "
          f"maps_athena.conf additions: {len(used_maps)}")

# ---- verify -------------------------------------------------------------------
def backport_files():
    return sorted(glob.glob(os.path.join(UA_ROOT, OUT_DIR, "*.txt")))

def npc_names(text):
    for s, f in def_lines(text):
        if f[1] in ("script", "shop", "cashshop") or f[1].startswith("duplicate("):
            yield f[2].split("::")[0].strip()

def references(text):
    for m in re.finditer(r'callfunc\s+"([^"]+)"', text):
        yield m.group(1)
    for m in re.finditer(r'duplicate\(([^)]+)\)', text):
        yield m.group(1)

def defined_names(text):
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        f = s.split("\t")
        if len(f) < 3:
            continue
        if f[0] == "function" and f[1] == "script":
            yield f[2].split("::")[0].strip(); continue
        if f[1] in ("script", "shop", "cashshop") or f[1].startswith("duplicate("):
            nm = f[2]
            yield nm.split("::")[0].strip()
            if "::" in nm:
                yield nm.split("::", 1)[1].strip()

def verify():
    mi = set()
    for line in read(os.path.join(UA_ROOT, "db", "map_index.txt")).splitlines():
        x = line.strip()
        if x and not x.startswith("//"):
            mi.add(x.split()[0])
    # names defined anywhere in uAthena npc/ (for ref resolution) + kafra base
    defined = {"kaf_alberta"}
    existing_names = Counter()
    for p in glob.glob(os.path.join(UA_ROOT, "npc", "**", "*.txt"), recursive=True):
        t = read(p)
        for n in defined_names(t):
            defined.add(n)
        if "/backport/re_cities/" not in p.replace("\\", "/"):
            for n in npc_names(t):
                existing_names[n] += 1
    miss_cmd, brace_bad, miss_ref, unreg = set(), [], set(), set()
    bp_names = Counter()
    for p in backport_files():
        t = read(p)
        # any still-live gap buildin (not commented) is a fatal miss (code only,
        # ignore string literals so dialogue prose isn't flagged as a live command)
        for ln in t.splitlines():
            if ln.strip().startswith("//"):
                continue
            idents = set(x.upper() for x in re.findall(r'[A-Za-z_]\w*', code_only(ln)))
            miss_cmd |= (idents & GAP_BUILTINS)
        if t.count("{") != t.count("}"):
            brace_bad.append(os.path.relpath(p, UA_ROOT))
        for n in npc_names(t):
            bp_names[n] += 1
        for r in references(t):
            if r not in defined:
                miss_ref.add(r)
        for s, f in def_lines(t):
            loc = f[0].split(",")[0]
            if loc not in mi:
                unreg.add(loc)
    name_coll = [(n, k, existing_names.get(n, 0)) for n, k in bp_names.items()
                 if k > 1 or existing_names.get(n, 0) > 0]
    print(f"live gap commands: {sorted(c.lower() for c in miss_cmd) or 'none'}")
    print(f"NPC name collisions: {name_coll or 'none'}")
    print(f"unresolved callfunc/duplicate refs: {sorted(miss_ref) or 'none'}")
    print(f"unregistered maps: {sorted(unreg) or 'none'}")
    print(f"brace-imbalanced files: {brace_bad or 'none'}")
    ok = not miss_cmd and not name_coll and not miss_ref and not unreg and not brace_bad
    print("VERIFY", "OK" if ok else "FAILED")
    return ok

# ---- selftest -----------------------------------------------------------------
def selftest():
    # consumeitem -> delitem
    t, ev = adapt_text("dewata,1,1,1\tscript\tX\t99,{\n\tconsumeitem 12043;\n\tclose;\n}\n")
    assert "delitem 12043,1;" in t, t
    assert any(k == "ADAPT" for k, *_ in ev), ev
    # gap buildin on its own line -> commented
    t2, ev2 = adapt_text("\tvip_status 1;\n")
    assert t2.strip().startswith("//[BACKPORT-GAP:vip_status]"), t2
    assert any(k == "COMMENT" for k, *_ in ev2), ev2
    # ET_ emotion -> commented
    t3, ev3 = adapt_text("\temotion ET_KIK;\n")
    assert "//[BACKPORT-GAP:ET_KIK]" in t3, t3
    # brace line with gap -> MANUAL (not auto-commented)
    t4, ev4 = adapt_text('\tif (vip_status(1)) { mes "hi"; }\n')
    assert any(k == "MANUAL" for k, *_ in ev4), ev4
    assert "{" in t4 and "}" in t4, t4
    # gap WORD inside mes dialogue must NOT be commented (string-literal guard)
    t5, ev5 = adapt_text('\tmes "leftovers used for fuel in cooking or heating";\n')
    assert not ev5 and "//[BACKPORT-GAP" not in t5, (t5, ev5)
    # site-fix: jeepney getargcount() loop -> getarg sentinel (no getargcount left)
    t6, ev6 = adapt_text('\tfor (.@i = 5; .@i < getargcount(); .@i++) {\n')
    assert "getargcount" not in t6 and 'getarg(.@i' in t6, t6
    assert any(k == "SITEFIX" for k, *_ in ev6), ev6
    # site-fix: Small Hole charat switch -> compare-based index (no charat left)
    t7, ev7 = adapt_text('\t\tswitch(atoi(charat(strnpcinfo(2),9))) {\n')
    assert "charat" not in t7 and 'compare(strnpcinfo(2),"mora1")' in t7, t7
    # boundary: NPC on a map absent from map_index -> commented (izlude_a not registered)
    t8, ev8 = adapt_text("izlude_a,182,218,4\tduplicate(Odgnalam)\tOdgnalam#iz_a\t554\n")
    assert t8.strip().startswith("//[BACKPORT-BOUNDARY:izlude_a]"), t8
    assert any(k == "BOUNDARY" for k, *_ in ev8), ev8
    # NPC on an in-scope registered map is NOT boundary
    t9, ev9 = adapt_text("dewata,100,100,4\tduplicate(X)\tY#z\t554\n")
    assert "BOUNDARY" not in t9 and not any(k == "BOUNDARY" for k, *_ in ev9), (t9, ev9)
    # CLASS A: '=' assignment -> set (incl. space-padded), but NOT '==' comparison
    tA, evA = adapt_text("\t.@mapName$        = getarg(0);\n")
    assert "set .@mapName$, getarg(0);" in tA and "=" not in tA.split("set",1)[1], tA
    assert any(t == "=->set" for _, t, _ in evA), evA
    tA2, _ = adapt_text("\tif (.@x == 5) end;\n")
    assert "set " not in tA2, tA2
    # CLASS B: self-target enablenpc()/disablenpc() -> ...npc strnpcinfo(0)
    tB, evB = adapt_text("\tenablenpc();\n")
    assert "enablenpc strnpcinfo(0);" in tB, tB
    assert any(t == "npc()->npc strnpcinfo(0)" for _, t, _ in evB), evB
    # CLASS D: for-init '=' and '++' -> uAthena set idiom
    tD, evD = adapt_text("\tfor (.@i = 5; .@i < 9; .@i++) end;\n")
    assert "for (set .@i,5;" in tD and "set .@i,.@i+1" in tD and "++" not in tD, tD
    # CLASS D guard: '--' inside a string literal must NOT be touched (no .@ anchor)
    tD2, _ = adapt_text('\tmes "Snort--";\n')
    assert 'mes "Snort--";' in tD2, tD2
    # combined: jeepney loop = site-fix (getargcount) + CLASS D (init/++) -> fully valid
    tJ, _ = adapt_text('\tfor (.@i = 5; .@i < getargcount(); .@i++) {\n')
    assert ("getargcount" not in tJ and "for (set .@i,5;" in tJ
            and "set .@i,.@i+1" in tJ), tJ
    # 'duplicate' is NOT a gap
    assert "DUPLICATE" not in GAP_BUILTINS
    # non_warp keeps script, drops warp defs
    nw = non_warp("a,1,1,0\twarp\tw1\t1,1,b,2,2\n-\tscript\tBase\t-1,{\n\tend;\n}\n")
    assert "warp" not in nw.split("\n")[0] if nw.split("\n")[0] else True
    assert "script\tBase" in nw, nw
    # kafra name normalization
    assert normalize_kafra_name("Kafra Employee::kaf_dewata") == "Kafra Employee#kaf_dewata"
    print("SELFTEST OK")

def main():
    if "--selftest" in sys.argv:
        selftest(); return
    if "--verify" in sys.argv:
        sys.exit(0 if verify() else 1)
    gen(); print("written.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the selftest, verify it passes**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-town-npcs.py --selftest`
Expected: `SELFTEST OK`. If a fixture fails, fix the corresponding function before proceeding (do NOT loosen the assert).

- [ ] **Step 3: Commit the tested generator**

```bash
cd /root/uAthena && git fetch && git rebase
git add dumps/forge/backport-renewal-town-npcs.py
git commit -m "$(cat <<'EOF'
backport: renewal town-NPC generator (parse+gap-adapt+kafra) [renewal-npc]

dumps/forge/backport-renewal-town-npcs.py: dynamic gap = rAthena-uAthena buildins,
consumeitem->delitem, other gap/ET_* -> commented+logged, kafra->duplicate(kaf_alberta).
Selftest green. No output generated yet (Task 3).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Generate town-NPCs, verify, wire, boot, document

**Files:**
- Create (generated): `npc/backport/re_cities/*.txt`, `Doc/backport_renewal_npc_gap.md`, `Doc/backport_renewal_warps_npc_changes.md`, `dumps/forge/backport-renewal-npc-includes.txt`
- Modify: `npc/scripts_athena.conf`

**Interfaces:**
- Consumes: `gen()`, `verify()` from Task 2.
- Produces: working renewal town-NPCs wired into the server.

- [ ] **Step 1: Generate**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-town-npcs.py`
Expected: a line like `zones: 6 | kafra duplicates: N | gap events: {'ADAPT': 6, 'COMMENT': ~30, 'MANUAL': ~?} | gap buildins known: ~340`. New files under `npc/backport/re_cities/`, `Doc/backport_renewal_npc_gap.md`, includes.

- [ ] **Step 2: Review the gap log (manual gate)**

Run: `cat Doc/backport_renewal_npc_gap.md`
Inspect every `MANUAL` event (gap token on a brace line — could not auto-comment). For each, manually edit the generated `npc/backport/re_cities/<zone>.txt` to neutralize the statement (e.g. replace `vip_status(1)` with `0`, or comment the whole NPC block) and note it. Re-run `--verify` after edits. `COMMENT`/`ADAPT` events are informational (testers assess lost flavor).

- [ ] **Step 3: Run static verify, confirm clean**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-town-npcs.py --verify`
Expected: `VERIFY OK` — `live gap commands: none`, `NPC name collisions: none`, `unresolved callfunc/duplicate refs: none`, `unregistered maps: none`, `brace-imbalanced files: none`.
If `live gap commands` is non-empty: a gap buildin slipped through `adapt_text` (likely brace-line MANUAL). Resolve in the generated file or extend the adapter, re-run.
If `unresolved refs` lists a name: a `duplicate(...)`/`callfunc` base is missing — confirm it's defined within the same output file; if it's an external rAthena util, port or stub it.

- [ ] **Step 4: Wire the NPC include block (append-only)**

```bash
cd /root/uAthena && { echo ""; echo "// ===== Backport renewal town-NPCs (GENERATED) ====="; cat dumps/forge/backport-renewal-npc-includes.txt; } >> npc/scripts_athena.conf
```
Verify: `tail -15 npc/scripts_athena.conf` shows the block (kaf_alberta base at line ~162 precedes our duplicates, so `duplicate(kaf_alberta)` resolves).

- [ ] **Step 4b: Wire the map load-list (append-only) — REQUIRED for materialization**

The server loads maps from `conf/maps_athena.conf` (a `map: <name>` list), NOT from
`map_index.txt` (which only assigns warp IDs). Renewal maps are absent from the load-list,
so NPCs/warps placed on them silently do not materialize (0 parse errors, 0 NPCs). Append
the 43 scope maps the generator collected:
```bash
cd /root/uAthena && { echo ""; echo "// ===== Backport renewal maps (GENERATED) ====="; cat dumps/forge/backport-renewal-maps-athena.txt; } >> conf/maps_athena.conf
```
Verify: `grep -cE '^map: ' conf/maps_athena.conf` rose by 43. (Each map still needs a
`.gat` in the GRF at deploy time; without it the server logs `Removing map [...]` and drops
it — a tester/deploy concern, same as pre-renewal warps.)

- [ ] **Step 5: Boot-parse verification (`--run_once`)**

`--run_once` parses all NPC then exits (no hang on the char link). MariaDB must be up.
```bash
cd /root/uAthena && set +e
timeout 120 ./map-server_sql --run_once > /tmp/r3_boot.log 2>&1
echo "exit: $?  | script errors: $(grep -icE 'script error' /tmp/r3_boot.log)"
grep -nE "script error on npc/backport/re_cities" /tmp/r3_boot.log    # MUST be empty
grep -oE "Removing map \[ (dewata|mora|malaya|dicastes0[12]|eclage|malangdo) \]" /tmp/r3_boot.log | head
grep -iE "Server is 'ready'" /tmp/r3_boot.log
set -e
```
Expected: `exit: 0`, **0 script errors** on `backport/re_cities`, `Server is 'ready'`.
Iterate parse fixes until 0 errors (this is where CLASS A/B/C/D, SITEFIX, BOUNDARY and
byte-preservation were discovered — boot-parse is the only thing that surfaces operator/
syntax gaps the token sanitizer misses). On the dev box the scope maps appear in
`Removing map [...]` (no renewal `.gat`) so town-NPCs do not materialize locally — expected;
materialization + walkthrough is the tester phase (needs a client + GRF with renewal maps).

- [ ] **Step 6: Write the change summary**

Create `Doc/backport_renewal_warps_npc_changes.md`:

```markdown
# Renewal warps + town-NPC backport — изменения

Источник: rAthena 7f08087. Ветка x64. 0 правок движка.

## Добавлено
- Статические варпы: <N> в npc/warps/backport/re/ (warp2->warp: <k>).
- Town-NPC: <M> сущностей в npc/backport/re_cities/ (6 зон + кафры).
- Кафры: <K> duplicate(kaf_alberta) из npc/re/kafras/kafras.txt.
- map_index: 0 добавлений (все scope-карты уже зарегистрированы).

## Адаптации синтаксиса (gap)
- consumeitem -> delitem,1: <a> мест (group B).
- Закомментировано+лог (group A no-op / C drop): <c> мест — см. Doc/backport_renewal_npc_gap.md.
- Ручная правка (MANUAL, brace-строки): <m> мест.
- duplicate — не gap (конструкция движка).

## Конфликты варпов
- ВХОД/ВЫХОД: <v>/<x> — см. Doc/backport_renewal_warp_conflicts.md (тестеры заполняют `решение?`).

## Верификация
- Оба генератора --selftest зелёные; --verify OK (имена/тайлы/endpoint/refs/braces).
- Локальный boot обоих серверов: 0 script-error на backport/re*, "Server is ready".
- За тестерами (нужен клиент): проходимость варпов, диалоги/транспорт, баланс, .gat новых карт.
```
Fill `<N>`,`<M>`,… from the Task 1/3 report lines and `git diff --stat`.

- [ ] **Step 7: Commit**

```bash
cd /root/uAthena && git fetch && git rebase
git add npc/backport/re_cities/ Doc/backport_renewal_npc_gap.md \
        Doc/backport_renewal_warps_npc_changes.md \
        dumps/forge/backport-renewal-npc-includes.txt npc/scripts_athena.conf
git commit -m "$(cat <<'EOF'
backport: renewal town-NPCs (6 zones) -> npc/backport/re_cities/ [renewal-npc]

189 town entities + scope kafras (duplicate(kaf_alberta)). rAthena-only tokens
adapted (consumeitem->delitem) or commented+logged. Verify OK, boots clean.
Changes -> Doc/backport_renewal_warps_npc_changes.md.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**1. Spec coverage (design §-by-§):**
- §3 locations / R1 → Task 1 Step 1 (sparse-checkout) + endpoint-completeness (`unreg` in `classify`, Steps 4/6). 0 additions confirmed.
- §4.1 warp2→warp → `parse_warp` accepts `warp2`, emits `warp`; selftest asserts it (Task 1 Step 2/3).
- §4.2 merge rule + conflict doc → `classify` name/tile collision → `Doc/backport_renewal_warp_conflicts.md` (separate from pre-renewal).
- §4.3 adaptation b/a/c + measured gap → `adapt_text` (consumeitem=B transform; other gap/ET_*=comment for A/C), dynamic `GAP_BUILTINS`, `duplicate` excluded; gap log.
- §4.4 R2/R3 input split → Task 1 parses only `warp`; Task 2 `non_warp()` + town + kafra.
- §4.5 isolation + append-only includes → output dirs + Steps 7 (Task1) / 4 (Task3).
- §5 verification → `--selftest`, `--verify`, endpoint, boot-parse, gap log — all present.
- Kafra (kafras.txt scope) → `kafra_lines()`, Task 3 generate.

**2. Placeholder scan:** No TBD/TODO; every code step shows complete runnable code; commands have expected output. Boot-parse references the local-cluster-boot-test method (environment-specific by nature) with concrete grep commands.

**3. Type consistency:** `parse_warp` dict keys (`srcmap`,`x`,`y`,`name`,`dstmap`,`warp2`) consistent across `classify`/`verify`/`selftest`. `adapt_text` returns `(text, events)` where `events` are `(kind, token, line)` tuples — consumed identically in `gen()` and `selftest()`. `GAP_BUILTINS` uppercase throughout. `def_lines`/`npc_names`/`references`/`defined_names` signatures match `backport-town-npcs.py` precedent.

**Known follow-ups (not blockers):** `MANUAL` brace-line gaps need human resolution (Task 3 Step 2); lost flavor from commented `getnpcid`/emotion statements is logged for testers; `.gat` for new maps is a deploy/client concern (design §5).
```

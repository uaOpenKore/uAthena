# SP-1 Renewal merchants + item-backport — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backport 55 renewal merchant-NPC files into uAthena, preceded by backporting the 93 renewal shop-items they sell that are missing from item_db.

**Architecture:** Two parts. **R1a**: a yml→TXT item converter (`backport-renewal-shop-items.py`, base = `backport-renewal-cards.py`) appends 93 items to `db/item_db2.txt` with script-sanitization. **R1b**: a merchant generator (`backport-renewal-merchants.py`, base = `backport-renewal-town-npcs.py`) emits adapted shop NPCs to `npc/backport/re_merchants/`, converting `marketshop`→`shop`, filtering still-missing items, and boundary-skipping unregistered renewal maps. 0 engine changes.

**Tech Stack:** Python 3 (stdlib), uAthena C map-server (`--run_once` boot-parse), rAthena `/tmp/rathena-ref` (commit 7f08087).

## Global Constraints

- **Source pinned:** rAthena `7f080871c8b3bbe7a79027194633201c63422ee1`, `/tmp/rathena-ref`. `npc/re/` + `db/re/` materialized (sparse-checkout).
- **No engine changes.** Data (item_db2.txt) + isolated NPC scripts only.
- **Additive + isolated:** item_db2.txt append-only; NPC output ONLY under `npc/backport/re_merchants/`; includes append-only in `npc/scripts_athena.conf` + `conf/maps_athena.conf`. Never modify existing files/order.
- **Generators write byte-preserving latin-1** for NPC/item TXT (8-bit EUC-KR dialogue); UTF-8 for Doc/ logs.
- **All docs → `Doc/`** (capital).
- **Before push:** `git fetch && git rebase` (Cline Bot pushes x64).
- **Commit footer:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Shell `set -e`+pipefail:** wrap grep/pgrep that may exit non-zero in `set +e`.
- **Spec:** `Doc/backport_renewal_sp1_merchants_design.md`. Roadmap: `Doc/backport_renewal_content_roadmap.md`.

**Measured facts (verified):** 509 items sold by IN merchants, 93 missing from item_db (script sanitizer: 43 keep / 15 drop→`{}` / 35 no-script). Entity types: shop 135 / script 306 / duplicate 611 / marketshop 44 / cashshop 0-in-IN. Placement: 388 placed / 99 floating. OUT files: cashmall.txt, cash_trader-idRO.txt, enchan_illusion_17_1.txt, mysterious_cookie_shop.txt (+ barters/*.yml). Unregistered renewal merchant maps (boundary): lhz_dun_n, paramk, rgsr_in, har_in01.

---

## File Structure

**Created:**
- `dumps/forge/backport-renewal-shop-items.py` — R1a converter (yml→item_db2.txt + sanitizer).
- `dumps/forge/backport-renewal-merchants.py` — R1b merchant generator.
- `npc/backport/re_merchants/*.txt` — generated merchant NPCs.
- `Doc/backport_renewal_shop_item_scripts.txt` — dropped item-script originals.
- `Doc/backport_renewal_merchants_gap.md` — adapted/commented/boundary log.
- `Doc/backport_renewal_sp1_merchants_changes.md` — change summary.
- `dumps/forge/backport-renewal-merchants-includes.txt`, `dumps/forge/backport-renewal-merchants-maps.txt`.

**Modified (append-only):** `db/item_db2.txt`, `npc/scripts_athena.conf`, `conf/maps_athena.conf`.

---

## Task 1 (R1a): Shop-item converter

**Files:**
- Create: `dumps/forge/backport-renewal-shop-items.py`
- Modify: `db/item_db2.txt` (append)
- Create: `Doc/backport_renewal_shop_item_scripts.txt`

**Interfaces:**
- Produces: 93 item rows appended to `db/item_db2.txt`; `collect_missing()` → set of int ids (reused conceptually by R1b's item-filter, which recomputes from the updated item_db).

- [ ] **Step 1: Materialize rAthena db/re (source setup)**

```bash
cd /tmp/rathena-ref && git sparse-checkout add db/re npc/re && \
  test -f db/re/item_db_etc.yml && echo "SETUP OK"
```
Expected: `SETUP OK`.

- [ ] **Step 2: Write the converter with selftest fixtures (test-first)**

Create `dumps/forge/backport-renewal-shop-items.py`:

```python
#!/usr/bin/env python3
"""SP-1a: backport renewal shop-items rAthena -> uAthena db/item_db2.txt.

Items = those SOLD by IN renewal merchants (npc/re/merchants, minus OUT files) and
MISSING from uAthena item_db.txt+item_db2.txt. Source: rAthena db/re/item_db_*.yml.
Scripts kept VERBATIM only if every token is known to uAthena (script_is_safe, the
backport-renewal-cards.py rule); else dropped to {} and logged.

Outputs: appends rows to db/item_db2.txt (between GENERATED markers, idempotent) +
Doc/backport_renewal_shop_item_scripts.txt (dropped-script originals).
Modes: --selftest | --dry-run | (default) generate. Run from repo root.
"""
import os, re, sys, glob, subprocess

UA = os.environ.get("UA_ROOT", ".")
RA = os.environ.get("RA_ROOT", "/tmp/rathena-ref")
OUT_FILES = {"cashmall.txt", "cash_trader-idRO.txt", "enchan_illusion_17_1.txt",
             "mysterious_cookie_shop.txt"}
TYPE = {"Healing": 0, "Usable": 2, "Etc": 3, "Weapon": 4, "Armor": 5, "Card": 6,
        "PetEgg": 7, "PetArmor": 8, "Ammo": 10, "DelayConsume": 11, "Cash": 18}
LOC = {"Head_Low": 1, "Right_Hand": 2, "Garment": 4, "Left_Accessory": 8, "Armor": 16,
       "Left_Hand": 32, "Shoes": 64, "Right_Accessory": 128, "Head_Top": 256,
       "Head_Mid": 512, "Both_Hand": 34, "Both_Accessory": 136}
GEN_HDR = "// ===== Backport renewal shop-items (GENERATED) ====="
GEN_END = "// ===== end renewal shop-items ====="

def rd(p):
    with open(p, encoding="latin-1") as f:
        return f.read()

# ---- uAthena KNOWN token set (sanitizer) — same construction as cards backport ----
def known_tokens():
    consts = {l.split()[0].upper() for l in rd(f"{UA}/db/const.txt").splitlines()
              if l.strip() and not l.startswith("//")}
    sc = rd(f"{UA}/src/map/script.c")
    buildins = {m.group(1).upper() for m in re.finditer(r'BUILDIN_DEF\(\s*(\w+)', sc)}
    buildins |= {m.group(1).upper() for m in re.finditer(r'BUILDIN_DEF2\(\s*\w+\s*,\s*"([^"]+)"', sc)}
    skills = set()
    for l in rd(f"{UA}/db/skill_db.txt").splitlines():
        p = l.split(",")
        if len(p) >= 16 and p[15].strip():
            skills.add(p[15].strip().upper())
    reserved = {w.upper() for w in (
        "if else for while switch case default break continue return end close close2 next "
        "mes menu select getarg set callfunc callsub input getrefine readparam getequipid "
        "BaseLevel JobLevel Class BaseClass Upper Sex Str Agi Vit Int Dex Luk Hp Sp MaxHp MaxSp "
        "Weight MaxWeight Zeny").split()}
    return consts | buildins | skills | reserved, skills

KNOWN, SKILLS = known_tokens()

def script_is_safe(s):
    if not s:
        return True
    if ".@" in s:                                  # uAthena parser has no scope vars
        return False
    if re.search(r'\bbonus\s+[A-Za-z_]\w*\s*;', s):  # 1-arg flag bonus; uAthena bonus is "ii"
        return False
    t = re.sub(r"[\$\.'#]*@?[A-Za-z_]\w*",
               lambda m: ' ' if re.match(r"[\$\.'#@]", m.group(0)) else m.group(0), s)
    for q in re.findall(r'"([^"]*)"', s):          # quoted strings in item scripts = skill names
        if q and q.upper() not in SKILLS:
            return False
    t = re.sub(r'"[^"]*"', ' ', t)
    for i in re.findall(r'[A-Za-z_]\w*', t):
        if i.upper() not in KNOWN:
            return False
    return True

# ---- collect item ids sold by IN merchants, missing from uAthena item_db ----
def ua_item_ids():
    ids = set()
    for fn in ("db/item_db.txt", "db/item_db2.txt"):
        p = os.path.join(UA, fn)
        if not os.path.exists(p):
            continue
        for ln in rd(p).splitlines():
            m = re.match(r'\s*(\d+),', ln)
            if m and not ln.lstrip().startswith("//"):
                ids.add(int(m.group(1)))
    return ids

def ra_show(relpath):
    return subprocess.run(["git", "-C", RA, "show", f"HEAD:{relpath}"],
                          capture_output=True).stdout.decode("latin-1")

def collect_missing():
    ua = ua_item_ids()
    sold = set()
    listing = subprocess.run(["git", "-C", RA, "ls-tree", "-r", "--name-only", "HEAD",
                              "npc/re/merchants/"], capture_output=True, text=True).stdout
    for f in listing.split("\n"):
        if not f.endswith(".txt") or os.path.basename(f) in OUT_FILES:
            continue
        for ln in ra_show(f).splitlines():
            p = ln.split("\t")
            if len(p) >= 4 and p[1] in ("shop", "marketshop"):
                for tok in p[3].split(",")[1:]:
                    m = re.match(r'(\d+):', tok.strip())
                    if m:
                        sold.add(int(m.group(1)))
    return {i for i in sold if i not in ua}

# ---- parse the missing items out of rAthena yml ----
def parse_items(missing):
    items = {}
    for yml in ("item_db_usable.yml", "item_db_equip.yml", "item_db_etc.yml"):
        path = os.path.join(RA, "db", "re", yml)
        if not os.path.exists(path):
            continue
        cur = None; inscr = False; scr = []
        def flush():
            if cur and cur["Id"] in missing:
                cur["Script"] = "\n".join(scr).strip()
                items[cur["Id"]] = cur
        for ln in rd(path).splitlines():
            m = re.match(r'\s*-\s*Id:\s*(\d+)', ln)
            if m:
                flush()
                cur = {"Id": int(m.group(1)), "Locs": [], "Script": ""}
                inscr = False; scr = []
                continue
            if cur is None:
                continue
            if inscr:
                if re.match(r'^    \w+:', ln) or re.match(r'^  - Id:', ln):
                    inscr = False
                else:
                    scr.append(ln.strip()); continue
            f = re.match(r'^    (\w+):\s*(.*)$', ln)
            if f:
                k, v = f.group(1), f.group(2).strip()
                if k == "Script" and v == "|":
                    inscr = True; scr = []
                elif k == "Locations":
                    cur["_sub"] = "loc"
                elif k in ("Jobs", "Classes", "Flags", "Trade", "Delay", "AliasName"):
                    cur["_sub"] = "other"
                else:
                    cur[k] = v; cur["_sub"] = None
                continue
            nm = re.match(r'^      (\w+):\s*(true|false)?', ln)
            if nm and cur.get("_sub") == "loc" and nm.group(2) in (None, "true"):
                cur["Locs"].append(nm.group(1))
        flush()
    return items

def loc_mask(it):
    m = 0
    for l in it.get("Locs", []):
        m |= LOC.get(l, 0)
    return m

def to_row(it):
    """rAthena yml item dict -> uAthena 22-field item_db2.txt CSV row + (dropped?, origscript)."""
    iid = it["Id"]
    aegis = it.get("AegisName", f"Item{iid}")
    name = (it.get("Name") or aegis).replace(",", " ").replace("{", "(").replace("}", ")")
    typ = TYPE.get(it.get("Type", "Etc"), 3)
    buy = it.get("Buy") or "0"
    weight = it.get("Weight") or "0"
    atk = it.get("Attack") or ""
    df = it.get("Defense") or ""
    rng = it.get("Range") or ""
    slots = it.get("Slots") or ""
    loc = loc_mask(it) or ""
    wlv = it.get("WeaponLevel") or ""
    elv = it.get("EquipLevelMin") or ""
    try:                                            # eLV>99 -> 99 (lv4 rule)
        if elv and int(elv) > 99:
            elv = "99"
    except ValueError:
        elv = ""
    view = it.get("View") or ""
    raw = it.get("Script", "")
    dropped = False
    if script_is_safe(raw):
        body = " ".join(x.strip() for x in raw.splitlines() if x.strip())
        script = "{ %s }" % body if body else "{}"
    else:
        script = "{}"; dropped = bool(raw)
    # ID,Aegis,Name,Type,Buy,Sell,Weight,ATK,DEF,Range,Slots,Job,Upper,Gender,Loc,wLV,eLV,Refine,View,{S},{},{}
    # Job=0xFFFFFFFF (all) — shop items; equip job-restriction logged for manual balance.
    row = (f"{iid},{aegis},{name},{typ},{buy},,{weight},{atk},{df},{rng},{slots},"
           f"0xFFFFFFFF,,,{loc},{wlv},{elv},,{view},{script},{{}},{{}}")
    return row, dropped, raw

def emit(rows, dropped_log):
    # idempotent append: strip any prior GENERATED block, then add fresh one
    path = os.path.join(UA, "db", "item_db2.txt")
    txt = rd(path)
    txt = re.sub(re.escape(GEN_HDR) + r".*?" + re.escape(GEN_END) + r"\n?", "", txt, flags=re.S)
    if not txt.endswith("\n"):
        txt += "\n"
    block = GEN_HDR + "\n" + "\n".join(rows) + "\n" + GEN_END + "\n"
    with open(path, "w", encoding="latin-1") as f:
        f.write(txt + block)
    with open(os.path.join(UA, "Doc", "backport_renewal_shop_item_scripts.txt"),
              "w", encoding="utf-8") as f:
        f.write("# Dropped renewal shop-item scripts (manual port). id<TAB>aegis<TAB>orig\n")
        f.write("\n".join(dropped_log) + "\n")

def build():
    missing = collect_missing()
    items = parse_items(missing)
    rows = []; dropped_log = []; kept = dropmissing = 0
    for iid in sorted(items):
        row, dropped, raw = to_row(items[iid])
        rows.append(row)
        if dropped:
            dropped_log.append(f"{iid}\t{items[iid].get('AegisName','')}\t{' '.join(raw.split())}")
        if items[iid].get("Script") and not dropped:
            kept += 1
    not_in_yml = sorted(missing - set(items))
    return rows, dropped_log, missing, items, kept, not_in_yml

def selftest():
    # sanitizer: compatible script kept, renewal/.@ dropped
    assert script_is_safe("heal 100,0;") is True
    assert script_is_safe("bonus bMaxHP,100;") is True
    assert script_is_safe(".@x = 5; heal .@x,0;") is False     # .@ scope var
    assert script_is_safe("specialeffect2 EF_NONSENSE_XYZ;") is False  # unknown token
    # type + loc mapping
    it = {"Id": 99999, "AegisName": "T", "Name": "Test", "Type": "Ammo",
          "Buy": "10", "Weight": "1", "Locs": ["Right_Hand"], "Script": "heal 1,0;"}
    row, dropped, raw = to_row(it)
    cols = row.split(",")
    assert cols[0] == "99999" and cols[3] == "10", cols          # id, Ammo type=10
    assert cols[11] == "0xFFFFFFFF", cols                        # job all
    assert dropped is False and "heal 1,0;" in row, row
    # eLV clamp
    it2 = {"Id": 1, "AegisName": "A", "Type": "Armor", "EquipLevelMin": "175",
           "Locs": ["Armor"], "Script": ""}
    r2, _, _ = to_row(it2)
    assert r2.split(",")[16] == "99", r2.split(",")            # eLV 175 -> 99
    assert r2.split(",")[14] == "16", r2.split(",")           # Loc Armor=16
    # dropped script -> {} + logged
    it3 = {"Id": 2, "AegisName": "B", "Type": "Usable", "Script": ".@y = 1;"}
    r3, d3, raw3 = to_row(it3)
    assert d3 is True and r3.split(",")[19] == "{}", r3
    print("SELFTEST OK")

def main():
    if "--selftest" in sys.argv:
        selftest(); return
    rows, dropped_log, missing, items, kept, not_in_yml = build()
    print(f"missing sold items: {len(missing)} | parsed from yml: {len(items)} | "
          f"rows: {len(rows)} | scripts kept: {kept} | dropped: {len(dropped_log)} | "
          f"not in yml: {not_in_yml or 'none'}")
    if "--dry-run" not in sys.argv:
        emit(rows, dropped_log)
        print("written.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run selftest, verify it passes**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-shop-items.py --selftest`
Expected: `SELFTEST OK`

- [ ] **Step 4: Dry-run against real data**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-shop-items.py --dry-run`
Expected: `missing sold items: 93 | parsed from yml: 93 | rows: 93 | scripts kept: 43 | dropped: 15 | not in yml: none`
If `not in yml` is non-empty: those ids aren't in re yml — investigate (maybe pre-re only); the count should be 0.

- [ ] **Step 5: Generate**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-shop-items.py`
Expected: report line + `written.`. Check `git diff --stat db/item_db2.txt` shows +~95 lines (93 rows + 2 markers).

- [ ] **Step 6: Boot item-load verification**

Run (MariaDB up):
```bash
cd /root/uAthena && set +e
timeout 120 ./map-server_sql --run_once > /tmp/r1a_boot.log 2>&1
echo "exit: $?"
# the 93 backported ids must NOT trigger 'does not exist / Using dummy'
grep -cE "does not exist|Using dummy data" /tmp/r1a_boot.log
grep -iE "item_db2|read.*item|Server is 'ready'" /tmp/r1a_boot.log | tail -3
set -e
```
Expected: server reaches ready; the dummy-data count should not have risen for the 93 ids (they now resolve). `git grep -c` the ids if needed. (Pre-existing unrelated warnings may remain.)

- [ ] **Step 7: Commit**

```bash
cd /root/uAthena && git fetch && git rebase
git add dumps/forge/backport-renewal-shop-items.py db/item_db2.txt Doc/backport_renewal_shop_item_scripts.txt
git commit -m "$(cat <<'EOF'
backport: 93 renewal shop-items -> item_db2.txt [renewal-merchants]

Converter dumps/forge/backport-renewal-shop-items.py (yml->TXT, base=cards). Items
sold by IN renewal merchants, missing from item_db. Scripts sanitized: 43 kept,
15 dropped->{} (logged Doc/), 35 no-script. eLV>99->99. 0 engine changes.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2 (R1b): Merchant generator

**Files:**
- Create: `dumps/forge/backport-renewal-merchants.py`
- Create: `npc/backport/re_merchants/*.txt`, `Doc/backport_renewal_merchants_gap.md`, includes/maps txt
- Modify: `npc/scripts_athena.conf`, `conf/maps_athena.conf`

**Interfaces:**
- Consumes: `db/item_db2.txt` (after R1a) for the defensive item-filter; `npc/re/merchants/*.txt` source.
- Produces: adapted merchant NPCs; `--selftest`/`--verify`/`gen`.

- [ ] **Step 1: Create the generator (reuse town-npcs core + merchant specifics)**

Create `dumps/forge/backport-renewal-merchants.py`. **Copy these functions VERBATIM from
`dumps/forge/backport-renewal-town-npcs.py`** (they are unchanged): `rd`/`read`, `write`,
`write_raw`, `load_buildins`, `UA_BUILTINS`/`RA_BUILTINS`/`GAP_BUILTINS`, `SITE_FIXES`,
`load_mapindex`/`UA_MAPS`, `code_only`, `adapt_text`, `def_lines`, `npc_names`, `references`,
`defined_names`. Then add the merchant-specific code below. Full file header + new code:

```python
#!/usr/bin/env python3
"""SP-1b: backport renewal merchant NPCs rAthena -> uAthena npc/backport/re_merchants/.

Reuses backport-renewal-town-npcs.py's adapt_text (syntax classes =/++/enablenpc()/
string-literal guard/SITEFIX/byte-preserve), token-gap, BOUNDARY (NPC on unregistered
map), write_raw (latin-1). Adds merchant specifics: marketshop->shop conversion, a
defensive item-filter (drop item ids absent from item_db after R1a), and the merchant
file-list (minus OUT files + barters/).
Outputs: npc/backport/re_merchants/<file>.txt + gap log + includes + maps list.
Modes: --selftest | --verify | (default) generate. Run from repo root.
"""
import os, re, sys, glob, subprocess
from collections import Counter

UA_ROOT = os.environ.get("UA_ROOT", ".")
RA_ROOT = os.environ.get("RA_ROOT", "/tmp/rathena-ref")
OUT_DIR = os.path.join("npc", "backport", "re_merchants")
OUT_FILES = {"cashmall.txt", "cash_trader-idRO.txt", "enchan_illusion_17_1.txt",
             "mysterious_cookie_shop.txt"}
SCOPE_MAP_PREFIXES = ("dewata", "dew_", "dicastes", "dic_", "eclage", "ecl_",
                      "malangdo", "mal_", "malaya", "ma_fild", "ma_in", "ma_dun",
                      "ma_scene", "ma_zif", "mora", "bif_fild")  # for maps_athena (collect)

# <<< PASTE VERBATIM from backport-renewal-town-npcs.py: rd/read, write, write_raw,
#     load_buildins, UA_BUILTINS, RA_BUILTINS, GAP_BUILTINS, SITE_FIXES, load_mapindex,
#     UA_MAPS, code_only, adapt_text, def_lines, npc_names, references, defined_names >>>

HEADER = ("//===== uAthena backport (renewal merchants, GENERATED) ======\n"
          "//= Port from rathena-ref; rAthena-only tokens adapted, marketshop->shop.\n"
          "//= DO NOT EDIT - regenerate via dumps/forge/backport-renewal-merchants.py\n"
          "//= Source: {src}\n"
          "//============================================================\n")

def ua_item_ids():
    ids = set()
    for fn in ("db/item_db.txt", "db/item_db2.txt"):
        p = os.path.join(UA_ROOT, fn)
        if not os.path.exists(p):
            continue
        for ln in read(p).splitlines():
            m = re.match(r'\s*(\d+),', ln)
            if m and not ln.lstrip().startswith("//"):
                ids.add(int(m.group(1)))
    return ids

UA_ITEMS = ua_item_ids()

def existing_npc_index():
    """Names + source tiles of every NON-backport-merchant uAthena NPC, for dedup: a
    renewal merchant whose NPC name OR tile already exists is a duplicate of a pre-renewal
    shop (refine/shops/refiners) -> skip (mirrors the warp merge-rule)."""
    names, tiles = set(), set()
    for p in glob.glob(os.path.join(UA_ROOT, "npc", "**", "*.txt"), recursive=True):
        if "/backport/re_merchants/" in p.replace("\\", "/"):
            continue
        t = read(p)
        for n in npc_names(t):
            names.add(n)
        for s, f in def_lines(t):
            tiles.add(tuple(f[0].split(",")[:3]))
    return names, tiles

EXIST_NAMES, EXIST_TILES = existing_npc_index()

def convert_shop_line(line):
    """marketshop->shop (drop :stock 3rd subfield) + defensive item-filter (drop ids
    absent from item_db). Returns (new_line, events). Works on a shop/marketshop def line:
    loc<TAB>shop|marketshop<TAB>name<TAB>SPRITE,id:price[:stock],id:price[:stock],..."""
    events = []
    f = line.split("\t")
    if len(f) < 4 or f[1] not in ("shop", "marketshop"):
        return line, events
    if f[1] == "marketshop":
        f[1] = "shop"; events.append(("MARKETSHOP", f[2], line.strip()))
    head, *rest = f[3].split(",")
    keep = [head]
    for tok in rest:
        m = re.match(r'(\d+):(-?\d+)(?::-?\d+)?$', tok.strip())  # id:price[:stock]
        if not m:
            keep.append(tok); continue
        iid = int(m.group(1))
        if iid not in UA_ITEMS:
            events.append(("ITEMFILTER", str(iid), line.strip())); continue  # drop missing
        keep.append(f"{m.group(1)}:{m.group(2)}")                # strip stock
    f[3] = ",".join(keep)
    return "\t".join(f), events

def block_filter(text):
    """Per NPC block (def-line .. its brace-closing line for script/function; the def
    line itself for duplicate/shop), decide its fate:
      DEDUP      - name or source tile already exists in uAthena -> duplicate of a
                   pre-renewal shop (refine/shops/refiners); comment out (skip).
      UNRESOLVED - still carries a live gap buildin after adaptation (deep renewal
                   expr: sprintf, refineui, stylist, ...); comment out (won't parse).
      keep       - otherwise (a genuinely new, portable renewal merchant).
    Commenting whole blocks keeps the file load-clean; both fates are logged."""
    lines = text.split("\n"); out = []; events = []; i = 0; n = len(lines)
    gone = set()   # names of commented renewal-only blocks (absent from uAthena) ->
                   # their duplicate(name) instances would orphan ("bad duplicate name")
    while i < n:
        ln = lines[i]; f = ln.split("\t")
        is_def = (len(f) >= 3 and
                  (("," in f[0] and not f[0].startswith("//")) or f[0] in ("function", "-")))
        if not is_def:
            out.append(ln); i += 1; continue
        if "{" in ln:                                  # multi-line script/function block
            depth = ln.count("{") - ln.count("}"); blk = [ln]; j = i + 1
            while j < n and depth > 0:
                blk.append(lines[j]); depth += lines[j].count("{") - lines[j].count("}"); j += 1
        else:                                          # single-line duplicate/shop
            blk = [ln]; j = i + 1
        # effective name: a label-only NPC '-\tscript\t::phs' has empty display name but
        # is referenced as 'phs' by duplicate(phs); use the label so dedup/orphan key on it
        # (and never dedup on an empty name).
        if len(f) > 2:
            parts = f[2].split("::")
            nm = parts[0].strip() or (parts[1].strip() if len(parts) > 1 else "")
        else:
            nm = ""
        tile = tuple(f[0].split(",")[:3]) if "," in f[0] else None
        mapname = f[0].split(",")[0] if "," in f[0] else None
        reason = None
        if (nm and nm in EXIST_NAMES) or (tile and tile in EXIST_TILES):
            reason = ("DEDUP", nm or "tile")
        elif mapname and mapname not in UA_MAPS:   # block-level boundary: NPC on a map not
            reason = ("BOUNDARY", mapname)          # in map_index (renewal dungeon/interior)
        else:
            code = code_only("\n".join(blk))
            live = {t.upper() for t in re.findall(r'[A-Za-z_]\w*', code)} & GAP_BUILTINS
            if live:
                reason = ("UNRESOLVED", ",".join(sorted(c.lower() for c in live)))
            else:
                # broken-syntax blocks uAthena's parser rejects even after adaptation
                # (deep renewal expr / source typos). Comment the whole block so its
                # duplicate() instances orphan cleanly via the orphan pass.
                for pat, label in ((r'\[[^\]]*(?:\+\+|--)', "incr-in-index"),
                                   (r'for\s*\([^;]*,[^;]*;', "malformed-for"),
                                   (r'select\(\s*$', "multiline-select"),
                                   (r'\([^()]*\?[^()]*\b[A-Za-z_]\w*\([^()]*\)[^()]*:', "ternary-funccall")):
                    if re.search(pat, code, re.M):
                        reason = ("UNRESOLVED", label); break
        if reason:
            tag = "//[BACKPORT-%s:%s] " % reason
            out += [b if b.strip().startswith("//") else tag + b for b in blk]
            events.append((reason[0], reason[1], nm or ln.strip()))
            if nm and nm not in EXIST_NAMES:   # commented & not in uAthena -> dups orphan
                gone.add(nm)
        else:
            out += blk
        i = j
    # orphan pass: comment duplicate(X) lines whose base X was commented above and is
    # absent from uAthena (else 'bad duplicate name (not exist)').
    if gone:
        out2 = []
        for ln in out:
            m = re.search(r'duplicate\(([^)]+)\)', ln)
            if m and m.group(1) in gone and not ln.strip().startswith("//"):
                out2.append("//[BACKPORT-ORPHAN:" + m.group(1) + "] " + ln)
                events.append(("ORPHAN", m.group(1), ln.strip()))
            else:
                out2.append(ln)
        out = out2
    return "\n".join(out), events

def adapt_merchant_text(text):
    """shop/marketshop conversion -> adapt_text (script syntax + BOUNDARY) -> block_filter
    (dedup duplicates of existing shops + comment unresolved renewal-feature blocks)."""
    pre = []; events = []
    for raw in text.splitlines():
        f = raw.split("\t")
        if len(f) >= 4 and f[1] in ("shop", "marketshop"):
            nl, ev = convert_shop_line(raw); pre.append(nl); events += ev
        else:
            pre.append(raw)
    body, ev2 = adapt_text("\n".join(pre))
    body, ev3 = block_filter(body)
    return body, events + ev2 + ev3

def merchant_files():
    out = []
    listing = subprocess.run(["git", "-C", RA_ROOT, "ls-tree", "-r", "--name-only", "HEAD",
                              "npc/re/merchants/"], capture_output=True, text=True).stdout
    for f in listing.split("\n"):
        if f.endswith(".txt") and os.path.basename(f) not in OUT_FILES and "/barters/" not in f:
            out.append(f)
    return out

def ra_show(rel):
    return subprocess.run(["git", "-C", RA_ROOT, "show", f"HEAD:{rel}"],
                          capture_output=True).stdout.decode("latin-1")

def port_global_functions():
    """Port the F_ utility functions renewal refiners call but uAthena lacks
    (F_getpositionname, F_IsCharm) from rAthena npc/other/Global_Functions.txt, adapted
    via adapt_text. Emitted as _renewal_functions.txt, included BEFORE the merchants so
    their paren-callfunc refs resolve. (A minimal SP-1 cross-dependency; the full
    Global_Functions port belongs to sub-project 3.)"""
    src = ra_show("npc/other/Global_Functions.txt")
    want = ("F_getpositionname", "F_IsCharm")
    lines = src.splitlines(); blocks = []; i = 0
    while i < len(lines):
        m = re.match(r'function\tscript\t(\w+)\t', lines[i])
        if m and m.group(1) in want:
            blk = [lines[i]]; i += 1
            while i < len(lines):
                blk.append(lines[i])
                if lines[i] == "}":
                    break
                i += 1
            blocks.append("\n".join(blk))
        i += 1
    body, _ = adapt_text("\n".join(blocks))
    return body

def gen():
    gap_buf = ["# Renewal merchants gap-лог (адаптации/marketshop/item-filter/boundary)\n\n"]
    includes = []; total = Counter()
    fbody = port_global_functions()
    if fbody.strip():
        write_raw(os.path.join(UA_ROOT, OUT_DIR, "_renewal_functions.txt"),
                  HEADER.format(src="npc/other/Global_Functions.txt (F_getpositionname, F_IsCharm)")
                  + fbody + "\n")
        includes.append("npc: npc/backport/re_merchants/_renewal_functions.txt")
    # pass 1: adapt every file, collect bodies
    bodies = {}; all_events = {}
    for rel in merchant_files():
        body, events = adapt_merchant_text(ra_show(rel))
        name = os.path.basename(rel)
        bodies[name] = body; all_events[name] = events
    # build the set of names AND labels still LIVE (defined by a non-commented base
    # anywhere in the output) plus everything uAthena already defines. Any duplicate(X)
    # whose X isn't in this set is an orphan (base commented / missing / label-only).
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
    live = set(EXIST_NAMES)
    for body in bodies.values():
        live |= defined_in(body)
    live.discard("")
    # pass 2: comment any duplicate(X) whose base X isn't live, then write
    for name in bodies:
        body = bodies[name]; ev = all_events[name]
        out2 = []
        for ln in body.split("\n"):
            m = re.search(r'duplicate\(([^)]+)\)', ln)
            if m and m.group(1).strip() not in live and not ln.strip().startswith("//"):
                out2.append("//[BACKPORT-ORPHAN:" + m.group(1).strip() + "] " + ln)
                ev.append(("ORPHAN", m.group(1).strip(), ln.strip()))
            else:
                out2.append(ln)
        body = "\n".join(out2)
        write_raw(os.path.join(UA_ROOT, OUT_DIR, name),
                  HEADER.format(src="npc/re/merchants/" + name) + body +
                  ("" if body.endswith("\n") else "\n"))
        includes.append(f"npc: npc/backport/re_merchants/{name}")
        if ev:
            gap_buf.append(f"\n## {name}\n")
            for kind, tok, ln in ev:
                total[kind] += 1
                gap_buf.append(f"- {kind} [{tok}] {ln}\n")
    # maps_athena additions: scope maps used by merchant placements
    used = set()
    for p in glob.glob(os.path.join(UA_ROOT, OUT_DIR, "*.txt")):
        for ln in read(p).splitlines():
            s = ln.strip()
            if not s or s.startswith("//") or s.startswith("function"):
                continue
            c = ln.split("\t")
            if "," in c[0] and not c[0].startswith("-"):
                used.add(c[0].split(",")[0])
    scope_maps = sorted(m for m in used if m.startswith(SCOPE_MAP_PREFIXES) and m in UA_MAPS)
    write(os.path.join(UA_ROOT, "dumps", "forge", "backport-renewal-merchants-maps.txt"),
          "\n".join("map: " + m for m in scope_maps) + "\n")
    write(os.path.join(UA_ROOT, "Doc", "backport_renewal_merchants_gap.md"), "".join(gap_buf))
    write(os.path.join(UA_ROOT, "dumps", "forge", "backport-renewal-merchants-includes.txt"),
          "\n".join(includes) + "\n")
    print(f"files: {len(includes)} | events: {dict(total)} | maps_athena additions: {len(scope_maps)}")

def backport_files():
    return sorted(glob.glob(os.path.join(UA_ROOT, OUT_DIR, "*.txt")))

def verify():
    mi = set()
    for ln in read(os.path.join(UA_ROOT, "db", "map_index.txt")).splitlines():
        x = ln.strip()
        if x and not x.startswith("//"):
            mi.add(x.split()[0])
    defined = set()
    existing = Counter()
    for p in glob.glob(os.path.join(UA_ROOT, "npc", "**", "*.txt"), recursive=True):
        t = read(p)
        for n in defined_names(t):
            defined.add(n)
        if "/backport/re_merchants/" not in p.replace("\\", "/"):
            for n in npc_names(t):
                existing[n] += 1
    miss_cmd, brace_bad, miss_ref, unreg, bad_item = set(), [], set(), set(), set()
    bp_names = Counter()
    for p in backport_files():
        t = read(p)
        for ln in t.splitlines():
            if ln.strip().startswith("//"):
                continue
            miss_cmd |= ({x.upper() for x in re.findall(r'[A-Za-z_]\w*', code_only(ln))} & GAP_BUILTINS)
        nc = "\n".join(l for l in t.splitlines() if not l.strip().startswith("//"))
        if code_only(nc).count("{") != code_only(nc).count("}"):  # braces in code only
            brace_bad.append(os.path.relpath(p, UA_ROOT))           # (mes "{" is prose)
        for n in npc_names(t):
            bp_names[n] += 1
        for r in references(nc):           # refs from live (non-commented) lines only
            if r not in defined:
                miss_ref.add(r)
        for s, f in def_lines(t):
            if f[0].split(",")[0] not in mi:
                unreg.add(f[0].split(",")[0])
            if f[1] in ("shop",) and len(f) >= 4:    # all sold ids must exist now
                for tok in f[3].split(",")[1:]:
                    m = re.match(r'(\d+):', tok.strip())
                    if m and int(m.group(1)) not in UA_ITEMS:
                        bad_item.add(int(m.group(1)))
    name_coll = [(n, k, existing.get(n, 0)) for n, k in bp_names.items()
                 if k > 1 or existing.get(n, 0) > 0]
    print(f"live gap commands: {sorted(c.lower() for c in miss_cmd) or 'none'}")
    print(f"NPC name collisions: {len(name_coll)}")
    print(f"unresolved refs: {sorted(miss_ref)[:20] or 'none'}")
    print(f"unregistered maps (placed, not boundary-commented): {sorted(unreg) or 'none'}")
    print(f"shop items still missing from item_db: {sorted(bad_item) or 'none'}")
    print(f"brace-imbalanced: {brace_bad or 'none'}")
    ok = not (miss_cmd or brace_bad or unreg or bad_item)
    print("VERIFY", "OK" if ok else "FAILED")
    return ok

def selftest():
    # marketshop -> shop + strip stock
    nl, ev = convert_shop_line("-\tmarketshop\tFoo\tFAKE_NPC,909:100:50,910:-1:-1")
    assert "\tshop\t" in nl and ":50" not in nl and ":-1:" not in nl, nl
    assert any(k == "MARKETSHOP" for k, *_ in ev), ev
    assert "909:100" in nl, nl
    # item-filter drops ids not in item_db (use an id guaranteed absent)
    nl2, ev2 = convert_shop_line("prt,1,1,1\tshop\tBar\t83,999999999:50,501:20")
    assert "999999999" not in nl2 and "501:20" in nl2, nl2
    assert any(k == "ITEMFILTER" for k, *_ in ev2), ev2
    # non-shop line untouched
    nl3, ev3 = convert_shop_line("prt,1,1,1\tscript\tBaz\t4_M_01,{ end; }")
    assert nl3.startswith("prt,1,1,1\tscript") and not ev3, (nl3, ev3)
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

- [ ] **Step 2: Run selftest**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-merchants.py --selftest`
Expected: `SELFTEST OK`. If `adapt_text`/`code_only`/etc. raise NameError, the verbatim paste from town-npcs.py is incomplete — copy the missing function.

- [ ] **Step 3: Generate**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-merchants.py`
Expected: `files: 55 | events: {'MARKETSHOP': ~44, 'ITEMFILTER': N, 'BOUNDARY': M, ...} | maps_athena additions: K`. Files appear under `npc/backport/re_merchants/`.

- [ ] **Step 4: Static verify**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-merchants.py --verify`
Expected: `VERIFY OK` — `live gap commands: none`, `unregistered maps: none` (placed-on-unregistered are BOUNDARY-commented), `shop items still missing: none` (R1a covered them), `brace-imbalanced: none`. If `live gap commands` non-empty, the gap survived adapt_text (likely a brace-line MANUAL) — resolve in the generated file or extend the adapter. If `shop items still missing` non-empty, R1a didn't cover an id — add it or rely on the item-filter (it should already drop it; investigate).

- [ ] **Step 5: Review gap log**

Run: `cat Doc/backport_renewal_merchants_gap.md`
Inspect BOUNDARY (merchants on lhz_dun_n/paramk/rgsr_in/har_in01 — expected, those maps aren't ported) and any MANUAL. Confirm no callshop orphans (a floating marketshop referenced by a boundary-commented placed NPC) — if found, note in the log; it's a tester concern.

- [ ] **Step 6: Wire includes (append-only)**

```bash
cd /root/uAthena
{ echo ""; echo "// ===== Backport renewal merchants (GENERATED) ====="; cat dumps/forge/backport-renewal-merchants-includes.txt; } >> npc/scripts_athena.conf
{ echo ""; echo "// ===== Backport renewal merchant maps (GENERATED) ====="; cat dumps/forge/backport-renewal-merchants-maps.txt; } >> conf/maps_athena.conf
```
Verify: `tail -5 npc/scripts_athena.conf` and `grep -c '^map: ' conf/maps_athena.conf` rose.

- [ ] **Step 7: Boot-parse verification**

```bash
cd /root/uAthena && set +e
timeout 120 ./map-server_sql --run_once > /tmp/r1b_boot.log 2>&1
echo "exit: $?  | script errors: $(grep -icE 'script error' /tmp/r1b_boot.log)"
grep -nE "script error on npc/backport/re_merchants" /tmp/r1b_boot.log     # MUST be empty
grep -icE "does not exist|Using dummy" /tmp/r1b_boot.log                   # shop items resolve
grep -iE "Server is 'ready'" /tmp/r1b_boot.log
set -e
```
Expected: `exit: 0`, 0 script errors on `re_merchants`, `Server is 'ready'`. Iterate parse fixes (CLASS A/B/D etc. already in adapt_text; new gaps → extend adapter and regen) until 0 errors. Renewal merchant maps appear in `Removing map` on the dev box (no `.gat`) — expected; materialization is the tester phase.

- [ ] **Step 8: Write change summary + commit**

Create `Doc/backport_renewal_sp1_merchants_changes.md` summarizing: 93 items added (43 scripts kept/15 dropped), 55 merchant files, marketshop→shop count, item-filter count, BOUNDARY count, maps_athena additions, verify+boot clean, tester notes (.gat, boundary-map ports, SQL regen). Then:
```bash
cd /root/uAthena && git fetch && git rebase
git add dumps/forge/backport-renewal-merchants.py npc/backport/re_merchants/ \
        Doc/backport_renewal_merchants_gap.md Doc/backport_renewal_sp1_merchants_changes.md \
        dumps/forge/backport-renewal-merchants-includes.txt dumps/forge/backport-renewal-merchants-maps.txt \
        npc/scripts_athena.conf conf/maps_athena.conf
git commit -m "$(cat <<'EOF'
backport: renewal merchants (55 files) -> npc/backport/re_merchants/ [renewal-merchants]

Generator on renewal-town-npcs base + merchant specifics: marketshop->shop (strip
stock), defensive item-filter, BOUNDARY-skip unregistered renewal maps (lhz_dun_n
etc). Syntax adapted via shared adapt_text. Verify OK, --run_once 0 script errors.
Wired scripts_athena.conf + maps_athena.conf. Changes -> Doc/.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**1. Spec coverage (design §-by-§):**
- §SP-1a item-добор → Task 1 (converter, sanitizer 43/15/35, item_db2 append, eLV99, dropped-log).
- §SP-1b магазины → Task 2 (generator, marketshop→shop, item-filter, boundary, re_merchants/).
- §Адаптация (syntax classes) → reused adapt_text from town-npcs (Task 2 Step 1 verbatim paste).
- §Изоляция/подключение → item_db2/scripts_athena/maps_athena append (Task 1 Step 5/7, Task 2 Step 6).
- §Верификация → --selftest/--verify/boot-parse (Task 1 Step 6, Task 2 Step 4/7).
- §OUT → OUT_FILES set + barters/ exclusion (both tasks).

**2. Placeholder scan:** No TBD/TODO; converter + merchant-specific code complete. The town-npcs verbatim-paste is a reference to an existing repo file (not a placeholder) — Task 2 Step 1 lists the exact functions and Step 2 selftest catches an incomplete paste.

**3. Type consistency:** `collect_missing()`/`parse_items()`/`to_row()` (Task 1) consistent. `convert_shop_line()` returns `(line, events)`, `adapt_merchant_text()` returns `(body, events)`, events are `(kind, token, line)` tuples consumed identically in `gen()` and `selftest()`. `UA_ITEMS`/`UA_MAPS`/`GAP_BUILTINS` uppercase/int sets used consistently. `adapt_text` returns `(text, events)` matching town-npcs contract.

**Known follow-ups (not blockers):** equip job-restriction defaulted to All (logged for manual balance); 15 dropped item-scripts need manual port; boundary-map merchants need those locations ported; SQL item-db regen is deploy.

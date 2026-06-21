# SP1 Town-NPC Backport — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backport the basic town NPCs of Moscovia/Brasilis/Manuk/Splendide from eathena-ref into uAthena additively, with zero changes to the script engine or existing NPCs.

**Architecture:** A deterministic Python generator copies the 4 towns' dedicated NPC files verbatim into an isolated `npc/backport/` subtree, extracts the moscovia/brasilis entries from the shared `shops.txt`, and rebuilds the two town kafras as `duplicate(kaf_alberta)` of uAthena's own kafra base (adapting away eathena-ref's newer 5-arg `F_Kafra` / storage-password API). It self-verifies (missing commands, NPC-name collisions, unresolved `callfunc`/`duplicate` refs, brace balance) and reports shop item IDs absent from item_db.

**Tech Stack:** Python 3 (build-time tool), uAthena NPC scripts, `npc/scripts_athena.conf`.

**Design spec:** `doc/backport_sp1_town_npcs_design.md` (committed `243b10f`).

**Branch:** `x64`. Run all commands from repo root `/root/uAthena`.

---

## File Structure

- **Create** `dumps/forge/backport-town-npcs.py` — generator (copy/extract/kafra-adapt/verify/items/selftest).
- **Create (generated, verbatim)** `npc/backport/cities/{moscovia,brasilis,manuk,splendide}.txt`, `npc/backport/merchants/{manuk,splendide}.txt`, `npc/backport/guides/{guides_mosk,guides_brasilis}.txt`.
- **Create (generated, extracted)** `npc/backport/merchants/shops_backport.txt` (moscovia/brasilis shop entries).
- **Create (generated, adapted)** `npc/backport/kafras/kafras_backport.txt` (2 `duplicate(kaf_alberta)` lines).
- **Create (generated)** `dumps/forge/backport-npc-includes.txt` (scripts_athena.conf splice lines).
- **Modify (guarded append only)** `npc/scripts_athena.conf`.
- **Create** `doc/backport_sp1_town_npcs_changes.md` — tester checklist + item-id report.

Existing NPC files and `src/map/script.c` are **never edited**.

---

## Task 1: Generator with selftest (TDD)

**Files:**
- Create: `dumps/forge/backport-town-npcs.py`

- [ ] **Step 1: Write the generator with a STUB `kafra_duplicates` and a built-in selftest**

Create `dumps/forge/backport-town-npcs.py` with exactly this content (`kafra_duplicates` is a stub — implemented in Step 3):

```python
#!/usr/bin/env python3
"""SP1 town-NPC backport: eathena-ref -> uAthena (Moscovia/Brasilis/Manuk/Splendide).

Copies the 4 towns' dedicated NPC files verbatim into npc/backport/, extracts the
moscovia/brasilis shop entries from the shared shops.txt, and rebuilds the two town
kafras as duplicate(kaf_alberta) of uAthena's own kafra base (adapting away
eathena-ref's newer F_Kafra / storage-password API). Verifies load-safety.

Modes: --selftest, --verify, --items-report, (default) generate.
Run from repo root. Python 3. See doc/backport_sp1_town_npcs_design.md.
"""
import os, re, sys, glob
from collections import Counter

UA_ROOT = os.environ.get("UA_ROOT", ".")
EA_ROOT = os.environ.get("EA_ROOT", "/tmp/eathena-ref")
BACKPORT = os.path.join("npc", "backport")

DEDICATED = [
    ("npc/cities/moscovia.txt",     "cities/moscovia.txt"),
    ("npc/cities/brasilis.txt",     "cities/brasilis.txt"),
    ("npc/cities/manuk.txt",        "cities/manuk.txt"),
    ("npc/cities/splendide.txt",    "cities/splendide.txt"),
    ("npc/merchants/manuk.txt",     "merchants/manuk.txt"),
    ("npc/merchants/splendide.txt", "merchants/splendide.txt"),
    ("npc/guides/guides_mosk.txt",  "guides/guides_mosk.txt"),
    ("npc/guides/guides_brasilis.txt", "guides/guides_brasilis.txt"),
]
SHOP_SRC  = "npc/merchants/shops.txt"
SHOP_MAPS = ("moscovia", "brasilis")
SHOP_OUT  = "merchants/shops_backport.txt"
KAFRA_SRCS = ["npc/kafras/kafras_mosk.txt", "npc/kafras/kafras_brasilis.txt"]
KAFRA_OUT  = "kafras/kafras_backport.txt"
KAFRA_BASE = "kaf_alberta"   # uAthena duplicatable kafra base (npc/kafras/kafras_alb.txt)

HEADER = ("//===== uAthena backport (SP1 town NPCs) =====================\n"
          "//= Port from eathena-ref; DO NOT EDIT - regenerate via\n"
          "//= dumps/forge/backport-town-npcs.py\n"
          "//= Source: {src}\n"
          "//============================================================\n")

def read(p):
    with open(p, encoding="latin-1") as f: return f.read()

def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: f.write(s)

def def_lines(text):
    """Yield (raw_line, tab_fields) for map-placed NPC definition lines."""
    for line in text.splitlines():
        s = line.rstrip("\n")
        t = s.strip()
        if not t or t.startswith("//"): continue
        f = s.split("\t")
        if len(f) >= 3 and "," in f[0]:
            yield s, f

def npc_names(text):
    for s, f in def_lines(text):
        if f[1] in ("script","shop","cashshop") or f[1].startswith("duplicate("):
            yield f[2].split("::")[0].strip()

def defined_names(text):
    """NPC names + ::export labels + function names (for reference resolution)."""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//"): continue
        f = s.split("\t")
        if len(f) < 3: continue
        if f[0] == "function" and f[1] == "script":
            yield f[2].split("::")[0].strip(); continue
        if f[1] in ("script","shop","cashshop") or f[1].startswith("duplicate("):
            nm = f[2]
            yield nm.split("::")[0].strip()
            if "::" in nm: yield nm.split("::",1)[1].strip()

def references(text):
    for m in re.finditer(r'callfunc\s+"([^"]+)"', text): yield m.group(1)
    for m in re.finditer(r'duplicate\(([^)]+)\)', text):  yield m.group(1)

def shop_item_ids(text):
    for s, f in def_lines(text):
        if f[1] not in ("shop","cashshop") or len(f) < 4: continue
        for part in f[3].split(",")[1:]:
            m = re.match(r'(\d+):', part.strip())
            if m: yield int(m.group(1))

def extract_shop_lines(text, maps):
    return [s for s, f in def_lines(text) if f[0].split(",")[0] in maps]

def normalize_kafra_name(name):
    if "::" in name:
        base, label = name.split("::", 1)
        return base + "#" + label
    return name

def kafra_duplicates():
    return []   # STUB — implemented in Task 1 Step 3

def load_cmds(path):
    txt = read(path)
    c = set(re.findall(r'BUILDIN_DEF\(([A-Za-z0-9_]+)', txt))
    c |= set(re.findall(r'BUILDIN_DEF2\([A-Za-z0-9_]+,"([A-Za-z0-9_]+)"', txt))
    return c

def load_item_ids():
    ids = set()
    for fn in ("db/item_db.txt", "db/item_db2.txt"):
        p = os.path.join(UA_ROOT, fn)
        if not os.path.exists(p): continue
        for line in read(p).splitlines():
            if line.lstrip().startswith("//"): continue
            m = re.match(r'\s*(\d+),', line)
            if m: ids.add(int(m.group(1)))
    return ids

def backport_files():
    return sorted(glob.glob(os.path.join(UA_ROOT, BACKPORT, "**", "*.txt"), recursive=True))

def gen():
    for ea_rel, bp_rel in DEDICATED:
        write(os.path.join(UA_ROOT, BACKPORT, bp_rel),
              HEADER.format(src=ea_rel) + read(os.path.join(EA_ROOT, ea_rel)))
    shop = extract_shop_lines(read(os.path.join(EA_ROOT, SHOP_SRC)), SHOP_MAPS)
    write(os.path.join(UA_ROOT, BACKPORT, SHOP_OUT),
          HEADER.format(src=SHOP_SRC) + "\n".join(shop) + "\n")
    kaf = kafra_duplicates()
    write(os.path.join(UA_ROOT, BACKPORT, KAFRA_OUT),
          HEADER.format(src="kafras_mosk+kafras_brasilis (adapted to "+KAFRA_BASE+")")
          + "\n".join(kaf) + "\n")
    incl = ["npc: npc/backport/" + bp for _, bp in DEDICATED] + \
           ["npc: npc/backport/" + SHOP_OUT, "npc: npc/backport/" + KAFRA_OUT]
    write(os.path.join(UA_ROOT, "dumps", "forge", "backport-npc-includes.txt"),
          "\n".join(incl) + "\n")
    print(f"generated {len(DEDICATED)} files, {len(shop)} shop lines, {len(kaf)} kafra duplicates")

def verify():
    ua = load_cmds(os.path.join(UA_ROOT, "src", "map", "script.c"))
    ea = load_cmds(os.path.join(EA_ROOT, "src", "map", "script.c"))
    gap = ea - ua
    mi = set()
    for line in read(os.path.join(UA_ROOT, "db", "map_index.txt")).splitlines():
        x = line.strip()
        if x and not x.startswith("//"): mi.add(x.split()[0])
    existing_names, defined, existing_tiles = Counter(), set(), set()
    for p in glob.glob(os.path.join(UA_ROOT, "npc", "**", "*.txt"), recursive=True):
        t = read(p)
        for n in defined_names(t): defined.add(n)
        if "/backport/" not in p.replace("\\","/"):
            for n in npc_names(t): existing_names[n] += 1
            for s, f in def_lines(t): existing_tiles.add(tuple(f[0].split(",")[:3]))
    miss_cmd, brace_bad, miss_ref = set(), [], set()
    bp_names, tile_overlap, unreg = Counter(), set(), set()
    for p in backport_files():
        t = read(p)
        miss_cmd |= (set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', t)) & gap)
        if t.count("{") != t.count("}"): brace_bad.append(os.path.relpath(p, UA_ROOT))
        for n in npc_names(t): bp_names[n] += 1
        for r in references(t):
            if r not in defined: miss_ref.add(r)
        for s, f in def_lines(t):
            loc = f[0].split(",")[0]
            if tuple(f[0].split(",")[:3]) in existing_tiles: tile_overlap.add(",".join(f[0].split(",")[:3]))
            if loc not in mi: unreg.add(loc)
        for m in re.findall(r'warp\s+"([^"]+)"', t):
            if m not in mi: unreg.add(m)
    name_coll = [(n,k,existing_names.get(n,0)) for n,k in bp_names.items()
                 if k > 1 or existing_names.get(n,0) > 0]
    print(f"missing commands: {sorted(miss_cmd) or 'none'}")
    print(f"NPC name collisions: {name_coll or 'none'}")
    print(f"unresolved callfunc/duplicate refs: {sorted(miss_ref) or 'none'}")
    print(f"unregistered maps referenced: {sorted(unreg) or 'none'}")
    print(f"brace-imbalanced files: {brace_bad or 'none'}")
    print(f"NPC tile overlaps with existing (informational): {sorted(tile_overlap) or 'none'}")
    ok = not miss_cmd and not name_coll and not miss_ref and not unreg and not brace_bad
    print("VERIFY", "OK" if ok else "FAILED")
    return ok

def items_report():
    ids = load_item_ids(); missing = set()
    for p in backport_files():
        for iid in shop_item_ids(read(p)):
            if iid not in ids: missing.add(iid)
    print(f"shop item IDs missing from item_db: {len(missing)}")
    if missing: print(" ", sorted(missing))
    return missing

def selftest():
    sample = ("prontera,1,1,1\tshop\tFoo\t83,501:10\n"
              "moscovia,5,5,3\tshop\tBar#m\t99,502:20,503:-1\n"
              "brasilis,2,2,2\tshop\tBaz\t100,504:5\n//c\n")
    sl = extract_shop_lines(sample, ("moscovia","brasilis"))
    assert len(sl) == 2 and all(l.split(",")[0] in ("moscovia","brasilis") for l in sl), sl
    assert sorted(shop_item_ids(sample)) == [501,502,503,504], sorted(shop_item_ids(sample))
    assert list(npc_names("moscovia,5,5,3\tscript\tOfficer#1::Lbl\t960,{")) == ["Officer#1"]
    assert normalize_kafra_name("Kafra Employee::kaf_bra") == "Kafra Employee#kaf_bra"
    assert normalize_kafra_name("Kafra Staff#mosk") == "Kafra Staff#mosk"
    kd = kafra_duplicates()
    assert len(kd) == 2, kd
    assert all("duplicate(kaf_alberta)" in l for l in kd), kd
    assert any(l.startswith("moscovia,223,191,4\t") for l in kd), kd
    print("SELFTEST OK")

def main():
    if "--selftest" in sys.argv: selftest(); return
    if "--verify" in sys.argv: sys.exit(0 if verify() else 1)
    if "--items-report" in sys.argv: items_report(); return
    gen(); print("written.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the selftest to verify it FAILS (stub kafra_duplicates)**

Run: `python3 dumps/forge/backport-town-npcs.py --selftest`
Expected: `AssertionError` at `assert len(kd) == 2` (stub returns `[]`).

- [ ] **Step 3: Implement `kafra_duplicates` (replace the stub)**

Replace the stub `def kafra_duplicates(): return []   # STUB ...` with:

```python
def kafra_duplicates():
    """Read eathena-ref kafra files; emit uAthena duplicate(kaf_alberta) lines
    (preserve map/coords/sprite/name, drop eathena-ref's newer kafra API)."""
    out = []
    for src in KAFRA_SRCS:
        for s, f in def_lines(read(os.path.join(EA_ROOT, src))):
            if f[1] != "script" or "kafra" not in f[2].lower(): continue
            sprite = f[3].split(",")[0].split("{")[0].strip()
            name = normalize_kafra_name(f[2])
            out.append(f"{f[0]}\tduplicate({KAFRA_BASE})\t{name}\t{sprite}")
    return out
```

- [ ] **Step 4: Run the selftest to verify it PASSES**

Run: `python3 dumps/forge/backport-town-npcs.py --selftest`
Expected: `SELFTEST OK`

- [ ] **Step 5: Commit the generator**

```bash
git add dumps/forge/backport-town-npcs.py
git commit -m "backport(npc): SP1 town-NPC generator (copy/extract/kafra-adapt/verify)

Copies the 4 towns' dedicated NPC files verbatim, extracts moscovia/brasilis
shop entries, rebuilds town kafras as duplicate(kaf_alberta) (old API). --verify
checks commands/names/refs/braces; --items-report flags shop items absent from
item_db; --selftest covers the transforms.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Generate and commit backport NPCs

**Files:**
- Create (generated): `npc/backport/**/*.txt`, `dumps/forge/backport-npc-includes.txt`

- [ ] **Step 1: Generate**

Run: `python3 dumps/forge/backport-town-npcs.py`
Expected: `generated 8 files, 6 shop lines, 2 kafra duplicates` then `written.`
(6 shop lines = moscovia 2 + brasilis 4; 2 kafra duplicates = moscovia + brasilis.)

- [ ] **Step 2: Inspect the adapted kafras and extracted shops**

Run: `cat npc/backport/kafras/kafras_backport.txt && echo '---' && cat npc/backport/merchants/shops_backport.txt`
Expected: kafra file has two lines —
`moscovia,223,191,4	duplicate(kaf_alberta)	Kafra Staff#mosk	114`
`brasilis,197,221,4	duplicate(kaf_alberta)	Kafra Employee#kaf_bra	117`
and the shops file has the moscovia (2) + brasilis (4) shop definitions.

- [ ] **Step 3: Confirm dedicated files were copied with the header**

Run: `head -6 npc/backport/cities/moscovia.txt && echo '...' && find npc/backport -name '*.txt' | sort`
Expected: header block + the original moscovia content; 10 files total (4 cities, 2 merchants, 2 guides, 1 shops_backport, 1 kafras_backport).

- [ ] **Step 4: Commit the generated NPCs**

```bash
git add npc/backport dumps/forge/backport-npc-includes.txt
git commit -m "backport(npc): generated SP1 town NPCs (Moscovia/Brasilis/Manuk/Splendide)

Verbatim cities/merchants/guides + extracted shops + adapted kafras in
npc/backport/. Engine untouched.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Verify load-safety; resolve any findings

**Files:** none unless a finding forces a fix.

- [ ] **Step 1: Run verify**

Run: `python3 dumps/forge/backport-town-npcs.py --verify`
Expected: `VERIFY OK` (missing commands: none; NPC name collisions: none; unresolved refs: none; unregistered maps: none; brace-imbalanced: none). The "NPC tile overlaps" line is informational (see Step 2).

- [ ] **Step 2: Resolve findings if `VERIFY FAILED`** (expected clean; act only on what prints)

  - **missing commands: [...]** — a backported NPC uses a script command uAthena lacks. Port it into `src/map/script.c` preserving the existing API (add `BUILDIN_DEF(name,"args")` + `int buildin_name(struct script_state *st)` in uAthena style; do NOT change any existing command), OR adapt the NPC to an equivalent existing command. Rebuild `make sql`.
  - **unresolved callfunc/duplicate refs: [...]** — a referenced function/base is absent. If it's a kafra/guide base, point the duplicate at uAthena's base (as kafras already do via `kaf_alberta`); if a `callfunc` target, port that function file into `npc/backport/` or adapt the call to uAthena's equivalent (e.g. eathena-ref's 5-arg `F_Kafra` → uAthena 3-arg). Re-run from Task 2 Step 1.
  - **unregistered maps referenced: [...]** — a backport NPC sits on, or warps to, a map missing from `db/map_index.txt`. Register it (append to map_index as in the maps/warps task) and re-run verify.
  - **NPC name collisions: [...]** — rename the backported NPC's `#hidden` suffix to be unique (edit the generator's output mapping), regenerate.
  - **brace-imbalanced files: [...]** — open the file; a `mes` string literal containing a stray `{`/`}` is a false positive (note and ignore); a real imbalance means the verbatim copy lost a line — re-copy.
  - **NPC tile overlaps (informational): [...]** — not a load error (eAthena allows multiple NPCs per tile). Review only if a backport NPC lands exactly on an existing NPC on a shared map (e.g. the alberta transport officer); relocate by 1 tile if it blocks an existing NPC. Otherwise leave as-is.

- [ ] **Step 3: Shop item-id dependency report**

Run: `python3 dumps/forge/backport-town-npcs.py --items-report`
Expected: a count + sorted list of shop item IDs absent from `db/item_db*.txt`. Record this list for Task 5 (the tester doc) and the separate items-backport task. A non-empty list does NOT block SP1 (the shop loads; missing items just won't be buyable).

---

## Task 4: Wire NPCs into the loader (guarded append)

**Files:**
- Modify (append only): `npc/scripts_athena.conf`

- [ ] **Step 1: Append backport includes (guarded, idempotent)**

Run:
```bash
grep -q 'npc/backport/' npc/scripts_athena.conf \
  && echo 'already present, skipping' \
  || { printf '\n// ===== Backport pre-renewal town NPCs (SP1, GENERATED includes) =====\n' >> npc/scripts_athena.conf; cat dumps/forge/backport-npc-includes.txt >> npc/scripts_athena.conf; echo appended; }
```
Expected: `appended`.

- [ ] **Step 2: Confirm append-only (nothing above changed)**

Run: `git diff npc/scripts_athena.conf | grep '^-' | grep -v '^---'`
Expected: empty (no removed/changed lines).

- [ ] **Step 3: Commit the wiring**

```bash
git add npc/scripts_athena.conf
git commit -m "backport(npc): load SP1 town NPCs via scripts_athena.conf (append-only)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Tester-facing change document

**Files:**
- Create: `doc/backport_sp1_town_npcs_changes.md`

- [ ] **Step 1: Capture the item-id report**

Run: `python3 dumps/forge/backport-town-npcs.py --items-report`
Note the printed count and list for the document below.

- [ ] **Step 2: Write the document**

Create `doc/backport_sp1_town_npcs_changes.md`. Replace `[ITEMS]` with the Step 1 output:

```markdown
# Бэкпорт NPC новых городов (SP1) — что изменено и что проверять

## Что изменено
- Добавлены городские NPC 4 локаций в изолированном `npc/backport/` (подключены через
  `scripts_athena.conf`, append-only): чиновники/транспорт, лавки, гайды, кафры.
  - **Moscovia / Brasilis** — дословный порт (города, гайды, лавки) + кафра как `duplicate(kaf_alberta)`.
  - **Manuk / Splendide** — городские NPC и лавки (дословно).
- **Движок не менялся** (0 новых скрипт-команд); существующие NPC и `script.c` не тронуты.
- Кафры новых городов сделаны `duplicate(kaf_alberta)` — поведение/набор услуг как у стандартной кафры
  uAthena (старый 3-арг `F_Kafra`); новый 5-арг API и пароль склада (`F_CheckKafCode`) из eathena-ref
  НЕ переносились (адаптация под старый API).

## Достижимость
- **Moscovia / Brasilis** — полностью: свободный транспорт-NPC (`warp "moscovia"/"brasilis"`).
- **Manuk / Splendide** — городские NPC на месте, но вход в Новый Мир квест-гейтед → откроется в **SP3**.

## Зависимости
- **item_db:** лавки ссылаются на item ID. Отсутствуют в item_db сейчас: **[ITEMS]**. Эти позиции не
  купить, пока их не добавит задача «бэкпорт итемов» (на загрузку шопа не влияет).

## Что проверять (на кластере, char-сервер + GRF)
1. Города грузятся; NPC видны на своих местах (координаты/спрайты как в источнике).
2. **Moscovia/Brasilis достижимы** через транспорт-NPC; обратный путь работает.
3. **Кафра** в Moscovia/Brasilis: сохранение, склад, телепорт — как у обычной кафры uAthena.
4. Лавки открываются; покупка имеющихся в item_db предметов работает.
5. Диалоги гайдов/чиновников проходят без ошибок скрипта в логе map-сервера.
6. Существующие NPC других городов не затронуты (выборочно).

## Воспроизведение
`python3 dumps/forge/backport-town-npcs.py` (идемпотентно). Проверки: `--selftest`, `--verify`,
`--items-report`. Дизайн — `doc/backport_sp1_town_npcs_design.md`.
```

- [ ] **Step 3: Commit the tester document**

```bash
git add doc/backport_sp1_town_npcs_changes.md
git commit -m "doc: tester checklist for SP1 town-NPC backport

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Push

- [ ] **Step 1: Push to origin/x64**

Run: `git push origin x64`
Expected: the SP1 commits (generator, generated NPCs, wiring, tester doc, [optional fix]) land on `origin/x64`.

---

## Notes for the implementer
- The generator only copies the enumerated files; it never edits existing NPCs or the engine.
- Re-running the generator is safe (backport files overwritten; the conf append is guarded).
- If `--verify` ever reports a missing command, that is the signal to port one script command into
  `script.c` **preserving the existing API** — this is expected to be zero for SP1.
- Manuk/Splendide reachability and all quest NPCs are out of SP1 scope (SP2 = quest-log engine, SP3 = quest NPCs).

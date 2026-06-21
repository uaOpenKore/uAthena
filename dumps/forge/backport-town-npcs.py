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

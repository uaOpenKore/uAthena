#!/usr/bin/env python3
"""Backport the items the generated npc/backport scripts give or check but uAthena lacks -> db/item_db2.txt.

Prod 2026-11-25: "buildin_getitem: Nonexistant item 22508 requested" (Eden Group Mark, re_eden/eden_common.txt:
the secretary takes the old mark 6219 and gives 22508, so the player lost it) and 6593 (novice vending machine).
Items = ids in getitem/getitem2/rentitem/getnameditem/countitem/delitem calls of npc/backport/**.txt, missing from
item_db.txt + item_db2.txt. Rows are made by backport-renewal-shop-items.py (same yml parser, type/loc mapping and
script sanitizer: scripts with tokens uAthena does not know become {} and are listed in
Doc/backport_renewal_script_item_scripts.txt). Own GENERATED block, idempotent.
Modes: --selftest | --dry-run | (default) generate. Run from repo root with RA_ROOT = a rAthena checkout.
"""
import importlib.util, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("shopitems", os.path.join(HERE, "backport-renewal-shop-items.py"))
si = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(si)
UA = si.UA
GEN_HDR = "// ===== Backport renewal script-items (GENERATED) ====="
GEN_END = "// ===== end renewal script-items ====="
CALL = re.compile(r'(?<![#\w."])(getitem2?|rentitem|getnameditem|countitem|delitem)\s*\(?\s*(\d+)\b')

def used_ids(text):
    ids = set()
    for ln in text.splitlines():
        code = ln.split("//")[0]
        for m in CALL.finditer(code):
            i = int(m.group(2))
            if i >= 500:  # below: never an item id here (getitem's are names like "#getitem1-1" or small vars)
                ids.add(i)
    return ids

def own_block_removed(txt):
    return re.sub(re.escape(GEN_HDR) + r".*?" + re.escape(GEN_END) + r"\n?", "", txt, flags=re.S)

def collect_missing():
    have = set()
    for fn in ("db/item_db.txt", "db/item_db2.txt"):
        for ln in own_block_removed(si.rd(os.path.join(UA, fn))).splitlines():
            m = re.match(r'\s*(\d+),', ln)
            if m and not ln.lstrip().startswith("//"):
                have.add(int(m.group(1)))
    used = set()
    for root, _, files in os.walk(os.path.join(UA, "npc", "backport")):
        for fn in files:
            if fn.endswith(".txt"):
                used |= used_ids(si.rd(os.path.join(root, fn)))
    return used - have

def emit(rows, dropped_log):
    path = os.path.join(UA, "db", "item_db2.txt")
    txt = own_block_removed(si.rd(path))
    if not txt.endswith("\n"):
        txt += "\n"
    with open(path, "w", encoding="latin-1") as f:
        f.write(txt + GEN_HDR + "\n" + "\n".join(rows) + "\n" + GEN_END + "\n")
    with open(os.path.join(UA, "Doc", "backport_renewal_script_item_scripts.txt"), "w", encoding="utf-8") as f:
        f.write("# Dropped renewal script-item scripts (manual port). id<TAB>aegis<TAB>orig\n")
        f.write("\n".join(dropped_log) + "\n")

WARP = re.compile(r'\s*warp\s+"(\w+)"\s*,\s*\d+\s*,\s*\d+\s*;\s*')

def plain_warp(raw, maps):
    m = WARP.fullmatch(raw or "")
    return bool(m) and m.group(1) in maps

def map_names():
    out = set()
    for ln in si.rd(os.path.join(UA, "db", "map_index.txt")).splitlines():
        c = ln.split()
        if c and not ln.startswith("//"):
            out.add(c[0])
    return out

def no_consume_ids(ids):
    out = set()
    path = os.path.join(si.RA, "db", "re", "item_db_usable.yml")
    for b in re.split(r"\n  - Id: ", si.rd(path))[1:]:
        m = re.match(r"(\d+)", b)
        if m and int(m.group(1)) in ids and re.search(r"^\s+NoConsume: true", b, re.M):
            out.add(int(m.group(1)))
    return out

# struct item's nameid is a short: an id above it wraps in an inventory (getitem 100072 -> a garbage item), so such
# items are left out and the script keeps failing safely with "Nonexistant item".
MAX_NAMEID = 32767

def build():
    maps = map_names()
    missing = {i for i in collect_missing() if i <= MAX_NAMEID}
    items = si.parse_items(missing)
    keep = no_consume_ids(set(items))
    rows, dropped_log = [], []
    for iid in sorted(items):
        row, dropped, raw = si.to_row(items[iid])
        if iid in keep:
            # NoConsume (Eden Group Mark, Warlock spell books): eAthena has no such flag, a usable row would be
            # used up on the first use -- keep it as an etc item without a script, like the old mark 6219.
            c = row.split(",")
            if c[3] in ("2", "11"):
                c[3] = "3"; row = ",".join(c)
                if not row.endswith(",{},{},{}"):
                    row = re.sub(r",\{[^{}]*\},\{\},\{\}$", ",{},{},{}", row)
                dropped_log.append(f"{iid}\t{items[iid].get('AegisName','')}\tNoConsume -> etc item, script dropped: {' '.join((raw or '').split())}")
                rows.append(row); continue
        if dropped and plain_warp(raw, maps) and row.endswith(",{},{},{}"):
            # the sanitizer does not know map names; a plain warp to a map uAthena has is safe (Eden Group Mark...)
            row = row[:-len("{},{},{}")] + "{ " + " ".join(raw.split()) + " },{},{}"; dropped = False
        rows.append(row)
        if dropped:
            dropped_log.append(f"{iid}\t{items[iid].get('AegisName','')}\t{' '.join(raw.split())}")
    return rows, dropped_log, missing, items

def selftest():
    t = ('\tgetitem 22508,1; //Para_Team_Mark_\n\tdonpcevent "#getitem1-1::OnCommandOn";\n'
         '\tif (countitem(6593) > 0) delitem 6219,1;\n\t// getitem 11111,1;\n\tgetitem .@id,1; getitem 3,1;\n')
    assert used_ids(t) == {22508, 6593, 6219}, used_ids(t)
    blk = "1,a\n" + GEN_HDR + "\n2,b\n" + GEN_END + "\n3,c\n"
    assert own_block_removed(blk) == "1,a\n3,c\n", own_block_removed(blk)
    assert plain_warp(' warp "moc_para01",171,115;', {"moc_para01"}) and not plain_warp('warp "nomap",1,1;', {"moc_para01"})
    assert not plain_warp('warp "moc_para01",1,1; heal 1,1;', {"moc_para01"})
    print("SELFTEST OK")

def main():
    if "--selftest" in sys.argv:
        selftest(); return
    rows, dropped_log, missing, items = build()
    print(f"missing script items: {len(missing)} | parsed from yml: {len(items)} | rows: {len(rows)} | "
          f"scripts dropped: {len(dropped_log)} | not in yml: {sorted(missing - set(items)) or 'none'}")
    if "--dry-run" not in sys.argv:
        emit(rows, dropped_log)
        print("written.")

if __name__ == "__main__":
    main()

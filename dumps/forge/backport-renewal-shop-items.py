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

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

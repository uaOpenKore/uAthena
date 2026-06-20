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
        # postfix/prefix ++/-- -> set var,var±1. Lookahead/behind guards keep us at
        # statement level: don't rewrite inside an array index like .@arr[.@i++] (the
        # ++ there is followed by ']'), which would inject a 'set' into a subscript.
        line = re.sub(r'(\.@\w+)\+\+(?=[;\s)]|$)', r'set \1,\1+1', line)
        line = re.sub(r'(\.@\w+)--(?=[;\s)]|$)', r'set \1,\1-1', line)
        line = re.sub(r'(?<=[(;\s])\+\+(\.@\w+)', r'set \1,\1+1', line)
        line = re.sub(r'(?<=[(;\s])--(\.@\w+)', r'set \1,\1-1', line)
        if line != before_d:
            events.append(("ADAPT", "for/incr->set", before_d.strip()))
        # VAR = a script variable: optional sigil (. $ ' #), optional @, name, optional $,
        # optional [index]. Covers .@x, $global, 'npc, #account, bare Zeny, .@a$[.@i].
        VAR = r"[.$'#]?@?\w+\$?(?:\[[^\]]*\])?"
        KW = ("if", "while", "for", "switch", "set", "else")
        # for-incr compound: for(...; var OP= expr) -> for(...; set var,var OP expr)
        line = re.sub(r'(for\s*\([^;]*;[^;]*;\s*)(' + VAR + r')\s*([+\-*/])=\s*([^)]+)\)',
                      lambda m: f'{m.group(1)}set {m.group(2)},{m.group(2)} {m.group(3)} {m.group(4)})',
                      line)
        # CLASS A-compound: 'var OP= expr;' -> 'set var, var OP expr;' (no compound assign)
        mc = re.match(r'^(\s*)(' + VAR + r')\s*([+\-*/])=\s*([^=].*?);(\s*//.*)?$', line)
        if mc and mc.group(2) not in KW:
            line = (f'{mc.group(1)}set {mc.group(2)}, {mc.group(2)} {mc.group(3)} '
                    f'{mc.group(4)};{mc.group(5) or ""}')
            events.append(("ADAPT", "op=->set", stripped))
        # callshop arity: uAthena sig "si" needs a flag; rAthena 1-arg (literal OR
        # concatenated name, paren or space form) -> normalize to: callshop <name>,1
        m_cs = re.match(r'^(\s*)callshop\s*\(?\s*(.+?)\s*\)?\s*;(\s*//.*)?$', line)
        if m_cs and "," not in re.sub(r'\([^()]*\)', '', m_cs.group(2)):  # no top-level comma = 1 arg
            line = f'{m_cs.group(1)}callshop {m_cs.group(2)},1;{m_cs.group(3) or ""}'
            events.append(("ADAPT", "callshop+flag", stripped))
        # movenpc arity: uAthena sig is "sii" (map,x,y); rAthena 4-arg adds a facing dir
        # -> drop the trailing dir argument.
        m_mv = re.sub(r'(\bmovenpc\s+"[^"]*"\s*,\s*\d+\s*,\s*\d+)\s*,\s*\d+(\s*;)', r'\1\2', line)
        if m_mv != line:
            line = m_mv
            events.append(("ADAPT", "movenpc-dropdir", stripped))
        # inline-if assignment: 'if (cond) var = val;' -> 'if (cond) set var, val;'
        mif = re.match(r'^(\s*if\s*\(.*?\)\s*)(' + VAR + r')\s*=\s*([^=].*?);(\s*//.*)?$', line)
        if mif:
            line = f'{mif.group(1)}set {mif.group(2)}, {mif.group(3)};{mif.group(4) or ""}'
            events.append(("ADAPT", "if-=->set", stripped))
        # CLASS A: rAthena '=' assignment -> uAthena 'set var, expr' (no '=' assignment).
        # Single '=' only ([^=] guard skips ==). VAR allows sigils/bare vars/index; trailing
        # // comment preserved. Keyword guard avoids matching control-flow heads.
        ma = re.match(r'^(\s*)(' + VAR + r')\s*=\s*([^=].*?);(\s*//.*)?$', line)
        if ma and ma.group(2) not in KW:
            line = f'{ma.group(1)}set {ma.group(2)}, {ma.group(3)};{ma.group(4) or ""}'
            events.append(("ADAPT", "=->set", stripped))
        # CLASS E: gap buildins used INSIDE expressions/conditions (uAthena lacks them) ->
        # replace the whole call with a safe constant so the line parses. Semantics degrade
        # (the condition becomes constant); logged. Balanced-paren match handles 1 nesting
        # level (e.g. inarray(.@x, getarg(0))). Only outside string literals.
        for fn_name, val in (("inarray", "-1"), ("countinarray", "0"),
                             ("isbegin_quest", "0"), ("jobcanentermap", "1"),
                             ("getequiprandomoption", "0"), ("checkmadogear", "0"),
                             ("checkdragon", "0"), ("checkwug", "0"), ("ismounting", "0"),
                             ("is_party_leader", "0"), ("guild_has_permission", "0"),
                             ("getequiparmorlv", "1")):
            if fn_name in line and ('"' not in line or fn_name in code_only(line)):
                new = re.sub(r'\b' + fn_name + r'\s*\([^()]*(?:\([^()]*\)[^()]*)*\)', val, line)
                if new != line:
                    line = new
                    events.append(("ADAPT", fn_name + "->" + val, stripped))
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
                                   (r'[A-Za-z_]\w*\(\s*$', "multiline-call"),
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

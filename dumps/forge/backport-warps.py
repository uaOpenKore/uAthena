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

def write_file(path, content):
    # UTF-8: warp/map_index output is ASCII; the conflict doc carries Cyrillic.
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
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
    fpath = os.path.join(EA_ROOT, "npc", "warps", "fields", "morroc_fild.txt")
    def mk(line):
        w = parse_warp(line); w["file"] = fpath; return w
    ua = [mk("moc_fild01,101,16,0\twarp\tmocf01-1\t15,3,moc_fild04,317,376"),
          mk("moc_fild04,213,327,0\twarp\tant001\t1,1,anthell01,35,267")]
    ea = [mk("moc_fild01,101,16,0\twarp\tmocf01-1\t15,3,moc_fild20,210,342"),
          mk("moc_fild21,26,196,0\twarp\tmocf020\t1,1,moc_fild20,349,179"),
          mk("moc_fild20,156,143,0\twarp\tant001\t1,1,anthell01,35,263")]
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

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

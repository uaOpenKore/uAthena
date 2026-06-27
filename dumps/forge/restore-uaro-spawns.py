#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
restore-uaro-spawns.py - re-merge the original uaRO mob spawns with the official
eAthena spawns, deduplicating by (map, mobID) so no mob gets double-spawned.

Background
----------
The live server only loads the official spawn set (npc/mobs/, via
scripts_monsters.conf).  The original uaRO custom placements live in
npc/mobs_uaro/ but were never loaded: scripts_main.conf imports
"scripts_monsters_uaro.conf" while the file on disk is
"scripts_monsters_uaro.conf_" (disabled).  Re-enabling it as-is would load BOTH
sets and double-spawn every mob that appears in both.

Policy (decided by the server owner)
------------------------------------
  * uaRO is AUTHORITATIVE on overlap.  For every (map, mobID) that exists in
    BOTH sets, the uaRO placement/density wins and the official spawn line(s)
    are removed from npc/mobs.
  * The official set stays only as a GAP-FILLER: (map, mobID) pairs that uaRO
    does NOT define (e.g. maps/mobs uaRO never covered) are kept untouched.
  * uaRO-only spawns come back simply by re-enabling the uaRO config.
  * Special extra spawns (npc/mobs_uaro/**/<name>_uaro.txt, e.g. c_tower_uaro)
    are purely ADDITIVE and are NOT part of the dedup key - they stack on top.
  * citycleaners / pvp / airplane uaRO files stay commented (as the original
    uaRO config left them); their official versions are untouched.

What this script does
---------------------
  * Builds the uaRO base (map, mobID) set from npc/mobs_uaro/{fields,dungeons}
    EXCLUDING *_uaro.txt special files.
  * Removes from every npc/mobs/**/*.txt every monster/boss_monster spawn line
    whose (map, mobID) is in that set.  Comments and gap-filler lines are kept.
  * Is idempotent: re-running after --apply is a no-op (overlap already gone).

The config re-enable (rename the .conf_, drop the duplicate c_tower_uaro
include) is done separately - this script only touches spawn data.

Usage
-----
  python3 restore-uaro-spawns.py [--root <repo>] [--apply] [--verbose]
Default is a dry run (reports counts, writes nothing).
"""
import argparse
import os
import re
import sys

MOB_DIR = os.path.join("npc", "mobs")
UARO_DIR = os.path.join("npc", "mobs_uaro")
SPAWN_TYPES = ("monster", "boss_monster")


def parse_spawn(line):
    """Return (map, mobid) for a monster/boss_monster spawn line, else None.

    Spawn line layout (whitespace-separated, tabs in practice):
        map,x,y,xs,ys <ws> <type> <ws> Mob Name <ws> id,amount,d1,d2[,event]
    The mob name may contain spaces, so the id lives in the LAST token.
    """
    s = line.strip()
    if not s or s.startswith("//"):
        return None
    toks = s.split()
    if len(toks) < 4:
        return None
    if toks[1] not in SPAWN_TYPES:
        return None
    head = toks[0].split(",")
    if not head:
        return None
    mapname = head[0].strip()
    last = toks[-1].split(",")
    mobid = last[0].strip()
    if not mapname or not re.fullmatch(r"\d+", mobid):
        return None
    return (mapname, mobid)


def collect_files(root, subdir, exclude_special):
    out = []
    base = os.path.join(root, subdir)
    for dirpath, _dirs, files in os.walk(base):
        for fn in sorted(files):
            if not fn.endswith(".txt"):
                continue
            if exclude_special and fn.endswith("_uaro.txt"):
                continue
            out.append(os.path.join(dirpath, fn))
    return sorted(out)


# Only these uaRO sub-trees are actually loaded by the (re-enabled) uaRO config.
# citycleaners.txt / pvp.txt / airplane.txt sit at the top level and stay
# commented out, so they must NOT contribute to the dedup key - otherwise the
# matching official lines would be stripped with no uaRO replacement loaded.
UARO_LOADED_SUBDIRS = (
    os.path.join(UARO_DIR, "fields"),
    os.path.join(UARO_DIR, "dungeons"),
)


def build_uaro_set(root, verbose=False):
    """(map, mobID) set from uaRO base files (excludes *_uaro.txt specials)."""
    keys = set()
    files = []
    for sub in UARO_LOADED_SUBDIRS:
        files.extend(collect_files(root, sub, exclude_special=True))
    files = sorted(files)
    for path in files:
        with open(path, "r", encoding="latin-1") as fh:
            for line in fh:
                k = parse_spawn(line)
                if k:
                    keys.add(k)
    if verbose:
        print("uaRO base files: %d, distinct (map,mobID): %d"
              % (len(files), len(keys)))
    return keys


def filter_official(root, uaro_keys, apply_changes, verbose=False):
    files = collect_files(root, MOB_DIR, exclude_special=False)
    total_removed = 0
    total_kept = 0
    touched = []
    for path in files:
        with open(path, "r", encoding="latin-1") as fh:
            lines = fh.readlines()
        new_lines = []
        removed = 0
        for line in lines:
            k = parse_spawn(line)
            if k is not None and k in uaro_keys:
                removed += 1
                continue
            new_lines.append(line)
        kept = sum(1 for ln in new_lines if parse_spawn(ln) is not None)
        total_removed += removed
        total_kept += kept
        if removed:
            touched.append((os.path.relpath(path, root), removed, kept))
            if apply_changes:
                with open(path, "w", encoding="latin-1", newline="") as fh:
                    fh.writelines(new_lines)
    if verbose:
        for rel, rem, kept in touched:
            print("  %-45s -%3d  (kept %d)" % (rel, rem, kept))
    print("Official files touched: %d" % len(touched))
    print("Official spawn lines removed (overlap -> uaRO wins): %d"
          % total_removed)
    print("Official spawn lines kept (gap-fillers): %d" % total_kept)
    return total_removed, total_kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root")
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry run)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(os.path.join(root, MOB_DIR)):
        print("error: %s not found under %s" % (MOB_DIR, root), file=sys.stderr)
        return 2
    uaro_keys = build_uaro_set(root, verbose=True)
    print("--- %s ---" % ("APPLY" if args.apply else "DRY RUN"))
    filter_official(root, uaro_keys, args.apply, verbose=args.verbose)
    if not args.apply:
        print("(dry run - no files written; pass --apply to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

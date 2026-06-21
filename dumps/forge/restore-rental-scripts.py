#!/usr/bin/env python3
# [Backport] Restore the rental-item scripts that were neutralized to {} in commit b0d885b
# now that the `rentitem` buildin exists (rental backport phase 2). Source of truth = the
# original item_db2 rows from the data-backport commit 25f3be3. For each box-item, inject the
# original `{ rentitem <id>,<seconds>; }` back into the Script column (the first {} on the line)
# of db/item_db.txt. Idempotent: a second run finds no neutralized rows and changes nothing.
# Run from repo root:  python3 dumps/forge/restore-rental-scripts.py
import re, subprocess, sys

# 1. recover (item-id -> rental script) from 25f3be3:db/item_db2.txt
orig = subprocess.run(['git', 'show', '25f3be3:db/item_db2.txt'],
                      capture_output=True, text=True).stdout.splitlines()
scripts = {}
for ln in orig:
    if 'rentitem' not in ln:
        continue
    mid = re.match(r'\s*(\d+),', ln)
    msc = re.search(r'(\{\s*rentitem[^}]*\})', ln)  # rental args contain a comma -> not CSV-split
    if mid and msc:
        scripts[mid.group(1)] = msc.group(1)
print("recovered %d rental scripts from 25f3be3" % len(scripts))

# 2. inject into the current db/item_db.txt (only fully-neutralized rows: ...,{},{},{})
path = 'db/item_db.txt'
out, restored = [], 0
for ln in open(path, encoding='utf-8', errors='replace'):
    mid = re.match(r'\s*(\d+),', ln)
    if mid and mid.group(1) in scripts and ',{},{},{}' in ln:
        ln = ln.replace('{}', scripts[mid.group(1)], 1)  # first {} = Script column
        restored += 1
    out.append(ln)
open(path, 'w', encoding='utf-8').write(''.join(out))
print("restored %d items in %s" % (restored, path))
if restored != len(scripts):
    print("WARN: restored(%d) != recovered(%d) - some IDs missing or already restored"
          % (restored, len(scripts)), file=sys.stderr)

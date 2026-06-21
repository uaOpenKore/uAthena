# SP-3 Small renewal NPC — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backport small renewal NPCs (7 new-zone guides + 12 `other/` files + taekwon) into uAthena, reusing the SP-1 merchant generator pattern.

**Architecture:** One generator `backport-renewal-smallnpc.py` assembled exactly like `backport-renewal-merchants.py` (town-npcs functions + merchant block_filter/orphan/existing-index), differing only in the input file-list (`smallnpc_sources()`) and output dir (`re_other/`). No marketshop/item-backport. 0 engine changes.

**Tech Stack:** Python 3, uAthena C map-server (`--run_once`), rAthena `/tmp/rathena-ref` (7f08087).

## Global Constraints

- Source pinned: rAthena `7f08087`, `/tmp/rathena-ref`, `npc/re/` materialized.
- No engine changes. Isolated output ONLY under `npc/backport/re_other/`; includes append-only in `npc/scripts_athena.conf` + `conf/maps_athena.conf`.
- Byte-preserving latin-1 for NPC TXT; UTF-8 for Doc/ logs.
- All docs → `Doc/`. Before push: `git fetch && git rebase` (Cline Bot). Commit footer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Spec: `Doc/backport_renewal_sp3_smallnpc_design.md`. Reuses SP-1 assets ([[backport-renewal-content-series]]): `dumps/forge/backport-renewal-town-npcs.py` (adapt_text) + `dumps/forge/backport-renewal-merchants.py` (block_filter, existing_npc_index, defined_in, orphan pass, convert_shop_line, verify).

**Measured facts:** guides 7 new zones (~736 lines). other IN: 12 files (~4.7K). taekwon 9 lines. token-gap small (charat/getnpcid/mergeitem/mesitemlink/mail/getargcount — covered by adapt_text CLASS E/COMMENT or block_filter UNRESOLVED). dimensional_gap NPCs on `dali` (not in map_index) → BOUNDARY. OUT: achievements/clans/CashShop_Functions/mercenary_rent/guides_woe_te.

---

## File Structure

**Created:** `dumps/forge/backport-renewal-smallnpc.py`, `npc/backport/re_other/*.txt`, `Doc/backport_renewal_smallnpc_gap.md`, `Doc/backport_renewal_sp3_smallnpc_changes.md`, `dumps/forge/backport-renewal-smallnpc-includes.txt`, `dumps/forge/backport-renewal-smallnpc-maps.txt`.
**Modified (append-only):** `npc/scripts_athena.conf`, `conf/maps_athena.conf`.

---

## Task 1: Small-NPC generator + output

**Files:**
- Create: `dumps/forge/backport-renewal-smallnpc.py`
- Create (generated): `npc/backport/re_other/*.txt`, gap log, includes, maps
- Modify: `npc/scripts_athena.conf`, `conf/maps_athena.conf`

**Interfaces:**
- Consumes: `backport-renewal-town-npcs.py` (adapt_text + helpers) + `backport-renewal-merchants.py` (block_filter, existing_npc_index, defined_in, convert_shop_line, verify-helpers) — assembled in, same as merchant build.
- Produces: adapted small-NPC files under `re_other/`.

- [ ] **Step 1: Assemble the generator (reuse town + merchant cores + small-NPC specifics)**

The generator is built by concatenation (same mechanism the merchant generator was assembled by): `backport-renewal-town-npcs.py` (minus its main-guard) + `backport-renewal-merchants.py`'s reusable functions (`read`/`write`/`write_raw` come from town; plus `ua_item_ids`/`UA_ITEMS`/`existing_npc_index`/`EXIST_NAMES`/`EXIST_TILES`/`convert_shop_line`/`block_filter`/`adapt_merchant_text`/`defined_in` from merchant) + the small-NPC specifics below. Concretely, the build script:

```python
# build-smallnpc.py logic (run once to assemble dumps/forge/backport-renewal-smallnpc.py)
import re
town = open('dumps/forge/backport-renewal-town-npcs.py', encoding='utf-8').read()
town = town.replace('\nif __name__ == "__main__":\n    main()\n', '\n')
merch = open('dumps/forge/backport-renewal-merchants.py', encoding='utf-8').read()
# take ONLY the merchant-specific reusable funcs (everything from the merchant marker block):
# ua_item_ids, UA_ITEMS, existing_npc_index, EXIST_NAMES/EXIST_TILES, convert_shop_line,
# block_filter, adapt_merchant_text, defined_in  -- they sit between the town paste and
# merchant gen()/verify()/main(). Slice from 'def ua_item_ids' up to (not incl.) 'def gen('.
m_start = merch.index('def ua_item_ids')
m_end = merch.index('def gen(')
merch_reuse = merch[m_start:m_end]
SMALL = open('/tmp/smallnpc_specific.py', encoding='utf-8').read()  # the block below
open('dumps/forge/backport-renewal-smallnpc.py', 'w', encoding='utf-8').write(
    town + '\n' + merch_reuse + '\n' + SMALL)
```

Small-NPC-specific block (`/tmp/smallnpc_specific.py`, becomes the tail of the generator):

```python
# ---- SP-3 small-NPC specifics ----
OUT_DIR = os.path.join("npc", "backport", "re_other")
GUIDES = ["dewata", "dicastes", "eclage", "malangdo", "malaya", "mora", "rockridge"]
OTHER_IN = ["TrainingZone123", "adven_boards", "dimensional_gap", "item_merge", "kachua_key",
            "mail", "pvp", "resetskill", "stone_change", "turbo_track", "bulletin_boards",
            "global_npcs"]
HEADER = ("//===== uAthena backport (renewal small-NPC, GENERATED) ======\n"
          "//= guides(new zones)+other+taekwon from rathena-ref; tokens adapted.\n"
          "//= DO NOT EDIT - regenerate via dumps/forge/backport-renewal-smallnpc.py\n"
          "//= Source: {src}\n"
          "//============================================================\n")

def smallnpc_sources():
    out = [f"npc/re/guides/guides_{g}.txt" for g in GUIDES]
    out += [f"npc/re/other/{o}.txt" for o in OTHER_IN]
    out += ["npc/re/jobs/taekwon.txt"]
    return out

def defined_in(body):
    """Names + ::labels of non-commented base NPCs in a body (for orphan detection).
    Merchant's gen() had this nested; define it module-level here for reuse."""
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

def gen():
    gap_buf = ["# Renewal small-NPC gap-лог (адаптации/dedup/boundary/unresolved/orphan)\n\n"]
    includes = []; total = Counter()
    bodies = {}; all_events = {}
    for rel in smallnpc_sources():
        body, events = adapt_merchant_text(ra_show(rel))   # ra_show is defined in merchant reuse
        name = os.path.basename(rel)
        bodies[name] = body; all_events[name] = events
    live = set(EXIST_NAMES)
    for body in bodies.values():
        live |= defined_in(body)
    live.discard("")
    for name in bodies:
        body = bodies[name]; ev = all_events[name]
        out2 = []
        for ln in body.split("\n"):
            mm = re.search(r'duplicate\(([^)]+)\)', ln)
            if mm and mm.group(1).strip() not in live and not ln.strip().startswith("//"):
                out2.append("//[BACKPORT-ORPHAN:" + mm.group(1).strip() + "] " + ln)
                ev.append(("ORPHAN", mm.group(1).strip(), ln.strip()))
            else:
                out2.append(ln)
        body = "\n".join(out2)
        write_raw(os.path.join(UA_ROOT, OUT_DIR, name),
                  HEADER.format(src="npc/re/.../" + name) + body +
                  ("" if body.endswith("\n") else "\n"))
        includes.append(f"npc: npc/backport/re_other/{name}")
        if ev:
            gap_buf.append(f"\n## {name}\n")
            for kind, tok, ln in ev:
                total[kind] += 1
                gap_buf.append(f"- {kind} [{tok}] {ln}\n")
    used = set()
    for p in glob.glob(os.path.join(UA_ROOT, OUT_DIR, "*.txt")):
        for ln in read(p).splitlines():
            s = ln.strip()
            if not s or s.startswith("//") or s.startswith("function"):
                continue
            c = ln.split("\t")
            if "," in c[0] and not c[0].startswith("-"):
                used.add(c[0].split(",")[0])
    scope_maps = sorted(m for m in used if m in UA_MAPS)
    write(os.path.join(UA_ROOT, "dumps", "forge", "backport-renewal-smallnpc-maps.txt"),
          "\n".join("map: " + m for m in scope_maps) + "\n")
    write(os.path.join(UA_ROOT, "Doc", "backport_renewal_smallnpc_gap.md"), "".join(gap_buf))
    write(os.path.join(UA_ROOT, "dumps", "forge", "backport-renewal-smallnpc-includes.txt"),
          "\n".join(includes) + "\n")
    print(f"files: {len(includes)} | events: {dict(total)}")

def backport_files():
    return sorted(glob.glob(os.path.join(UA_ROOT, OUT_DIR, "*.txt")))

def verify():
    mi = set()
    for ln in read(os.path.join(UA_ROOT, "db", "map_index.txt")).splitlines():
        x = ln.strip()
        if x and not x.startswith("//"):
            mi.add(x.split()[0])
    defined = set()
    for p in glob.glob(os.path.join(UA_ROOT, "npc", "**", "*.txt"), recursive=True):
        for n in defined_names(read(p)):
            defined.add(n)
    miss_cmd, brace_bad, miss_ref, unreg = set(), [], set(), set()
    for p in backport_files():
        t = read(p)
        nc = "\n".join(l for l in t.splitlines() if not l.strip().startswith("//"))
        for ln in nc.splitlines():
            miss_cmd |= ({x.upper() for x in re.findall(r'[A-Za-z_]\w*', code_only(ln))} & GAP_BUILTINS)
        if code_only(nc).count("{") != code_only(nc).count("}"):
            brace_bad.append(os.path.relpath(p, UA_ROOT))
        for r in references(nc):
            if r not in defined:
                miss_ref.add(r)
        for s, f in def_lines(t):
            if f[0].split(",")[0] not in mi:
                unreg.add(f[0].split(",")[0])
    print(f"live gap commands: {sorted(c.lower() for c in miss_cmd) or 'none'}")
    print(f"unresolved refs: {sorted(miss_ref)[:20] or 'none'}")
    print(f"unregistered maps: {sorted(unreg) or 'none'}")
    print(f"brace-imbalanced: {brace_bad or 'none'}")
    ok = not (miss_cmd or brace_bad or unreg)
    print("VERIFY", "OK" if ok else "FAILED")
    return ok

def main():
    if "--selftest" in sys.argv:
        # smoke: sources resolvable + adapt pipeline importable
        srcs = smallnpc_sources()
        assert len(srcs) == 20, srcs            # 7 guides + 12 other + 1 taekwon
        assert "DUPLICATE" not in GAP_BUILTINS
        print("SELFTEST OK"); return
    if "--verify" in sys.argv:
        sys.exit(0 if verify() else 1)
    gen(); print("written.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the build assembler + selftest**

```bash
cd /root/uAthena
# write the small-NPC specific block to /tmp, then assemble
# (the block above is the content of /tmp/smallnpc_specific.py)
python3 - <<'ASM'
import re
town=open('dumps/forge/backport-renewal-town-npcs.py',encoding='utf-8').read().replace('\nif __name__ == "__main__":\n    main()\n','\n')
merch=open('dumps/forge/backport-renewal-merchants.py',encoding='utf-8').read()
reuse=merch[merch.index('def ua_item_ids'):merch.index('def gen(')]
small=open('/tmp/smallnpc_specific.py',encoding='utf-8').read()
open('dumps/forge/backport-renewal-smallnpc.py','w',encoding='utf-8').write(town+'\n'+reuse+'\n'+small)
print("assembled")
ASM
UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-smallnpc.py --selftest
```
Expected: `assembled` + `SELFTEST OK`. If NameError on a helper, the merchant slice (`ua_item_ids`..`gen`) missed a function — widen the slice or paste it.

- [ ] **Step 3: Generate**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-smallnpc.py`
Expected: `files: 20 | events: {...DEDUP/BOUNDARY/UNRESOLVED/ORPHAN/ADAPT...}`. Files under `npc/backport/re_other/`.

- [ ] **Step 4: Static verify**

Run: `cd /root/uAthena && UA_ROOT=. RA_ROOT=/tmp/rathena-ref python3 dumps/forge/backport-renewal-smallnpc.py --verify`
Expected: `VERIFY OK` (live gap none, unreg none — dali/unreg-maps BOUNDARY-commented, brace none). If `live gap commands` non-empty, the gap survived adapt — extend adapt_text (in town-npcs.py) and re-assemble. If `unregistered maps` non-empty, the block_filter BOUNDARY didn't fire for a placed NPC — confirm its map isn't in map_index.

- [ ] **Step 5: Wire includes (append-only)**

```bash
cd /root/uAthena
grep -q "Backport renewal small-NPC" npc/scripts_athena.conf || { echo ""; echo "// ===== Backport renewal small-NPC (GENERATED) ====="; cat dumps/forge/backport-renewal-smallnpc-includes.txt; } >> npc/scripts_athena.conf
grep -q "Backport renewal small-NPC maps" conf/maps_athena.conf || { echo ""; echo "// ===== Backport renewal small-NPC maps (GENERATED) ====="; cat dumps/forge/backport-renewal-smallnpc-maps.txt; } >> conf/maps_athena.conf
```

- [ ] **Step 6: Boot-parse verification**

```bash
cd /root/uAthena && set +e
timeout 120 ./map-server_sql --run_once > /tmp/sp3_boot.log 2>&1
echo "exit: $? | errors on re_other: $(grep -cE 'script error on npc/backport/re_other' /tmp/sp3_boot.log) | bad-dup: $(grep -icE 'bad duplicate.*re_other' /tmp/sp3_boot.log)"
grep -iE "Server is 'ready'" /tmp/sp3_boot.log
set -e
```
Expected: `exit: 0`, 0 errors on `re_other`, Server ready. Iterate (extend adapt_text / block_filter) until 0; renewal/dali maps appear in `Removing map` on dev box (no .gat) — expected.

- [ ] **Step 7: Write change summary + commit**

Create `Doc/backport_renewal_sp3_smallnpc_changes.md` (counts: guides/other/taekwon files live, DEDUP/BOUNDARY/UNRESOLVED/ORPHAN, dali closed, tester notes). Then:
```bash
cd /root/uAthena && git fetch && git rebase
git add dumps/forge/backport-renewal-smallnpc.py npc/backport/re_other/ \
        dumps/forge/backport-renewal-smallnpc-includes.txt dumps/forge/backport-renewal-smallnpc-maps.txt \
        Doc/backport_renewal_smallnpc_gap.md Doc/backport_renewal_sp3_smallnpc_changes.md \
        npc/scripts_athena.conf conf/maps_athena.conf
git commit -m "$(cat <<'EOF'
backport: renewal small-NPC (guides+other+taekwon) -> npc/backport/re_other/ [renewal-smallnpc]

Generator reuses SP-1 adapt_text + block_filter. 7 new-zone guides + 12 other files +
taekwon. dimensional_gap closes the dali boundary. Verify OK, --run_once 0 script errors.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**1. Spec coverage:** guides 7 zones + other 12 IN + taekwon → `smallnpc_sources()` (Step 1). OUT (achievements/clans/CashShop/mercenary_rent/woe_te) → excluded from OTHER_IN/GUIDES. adapt+block_filter reuse → assembled (Step 1). dali BOUNDARY → block_filter mapname-not-in-UA_MAPS (reused). Isolation/verify/boot → Steps 4-6.

**2. Placeholder scan:** No TBD; the generator is assembled from two existing tested files + a complete small-NPC block. The slice indices (`def ua_item_ids`..`def gen(`) are exact string anchors present in the committed merchant generator.

**3. Type consistency:** `adapt_merchant_text`/`block_filter`/`defined_in`/`ra_show`/`existing_npc_index`/`EXIST_NAMES`/`UA_MAPS`/`GAP_BUILTINS`/`code_only`/`def_lines`/`references`/`defined_names`/`write_raw`/`read` all come from the town+merchant paste and are used with their existing signatures. `gen`/`verify`/`main`/`backport_files`/`OUT_DIR`/`HEADER` are redefined in the small-NPC tail (last definition wins).

**Known follow-ups:** charat/mergeitem/mesitemlink/mail blocks UNRESOLVED-commented (logged); dali/renewal-guide maps need .gat (tester).

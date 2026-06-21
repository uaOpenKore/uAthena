#!/usr/bin/env python3
# [Backport] Renewal CARDS dropped by backported renewal mobs -> uAthena item_db2 (CSV).
# Source: rAthena master commit 7f080871c8b3bbe7a79027194633201c63422ee1 (2026-06-18),
#         db/re/item_db_etc.yml (Type: Card) + db/re/mob_db.yml (drop refs).
# Rule (per request, "old rules" = lv4 precedent):
#   - additive: only cards NOT already in uAthena (item_db.txt | item_db2.txt), and dropped
#     by a re-candidate mob (mob not in uAthena mob_db.txt). No engine / no new mechanics.
#   - card SCRIPT kept VERBATIM only if EVERY identifier token is known to uAthena
#     (const.txt consts U script.c buildins U skill_db skills U script keywords/params).
#     Any renewal-only token (bMatk, bUseSPAmount, an unknown skill name, ...) -> whole
#     script dropped to {} (card becomes collectible; the drop resolves, load stays clean).
#   - original scripts preserved for manual porting in Doc/backport_renewal_card_scripts.txt
# Outputs: /tmp/renewal_cards.txt (CSV)  +  /tmp/renewal_card_scripts_orig.txt
import re

UA = '/root/uAthena/db'
RA = '/tmp/rathena-ref/db'

# ---- uAthena known token sets -------------------------------------------------
ua_item_ids = set(); ua_item_aegis = set()
for fn in ('item_db.txt', 'item_db2.txt'):
    for ln in open(f'{UA}/{fn}', encoding='utf-8', errors='replace'):
        if ln.startswith('//') or ',' not in ln: continue
        p = ln.split(',')
        if len(p) < 4: continue
        try: ua_item_ids.add(int(p[0]))
        except: continue
        ua_item_aegis.add(p[1].strip().upper())

consts = set()
for ln in open(f'{UA}/const.txt', encoding='utf-8', errors='replace'):
    ln = ln.strip()
    if not ln or ln.startswith('//'): continue
    consts.add(ln.split()[0].upper())

buildins = set()
_sc_src = open(f'{UA}/../src/map/script.c', encoding='utf-8', errors='replace').read()
for m in re.finditer(r'BUILDIN_DEF\(\s*(\w+)', _sc_src):           # BUILDIN_DEF(name,...)
    buildins.add(m.group(1).upper())
for m in re.finditer(r'BUILDIN_DEF2\(\s*\w+\s*,\s*"([^"]+)"', _sc_src):  # BUILDIN_DEF2(func,"scriptname",...)
    buildins.add(m.group(1).upper())                              # bonus2/bonus3/bonus4/bonus5, ...

skills = set()
for ln in open(f'{UA}/skill_db.txt', encoding='utf-8', errors='replace'):
    if ln.startswith('//') or ',' not in ln: continue
    p = ln.split(',')
    if len(p) >= 16:
        nm = p[15].strip()
        if nm: skills.add(nm.upper())

# script syntax keywords + permanent/reserved script parameters (not in const.txt)
RESERVED = {w.upper() for w in (
    'if else for while do switch case default break continue return end close close2 next '
    'mes menu select goto function set getarg input '
    'BaseLevel JobLevel BaseExp JobExp NextBaseExp NextJobExp BaseClass Class Upper Sex Zeny '
    'Weight MaxWeight Hp MaxHp Sp MaxSp Karma Manner StatusPoint SkillPoint BaseJob Job '
    'Str Agi Vit Int Dex Luk PerfectHitRate Hit Flee Flee2 Def Mdef Atk Matk Aspd Crit '
    'Range Speed AdminClass'
).split()}

KNOWN = consts | buildins | skills | RESERVED

def script_is_safe(sc):
    if not sc: return True
    if '.@' in sc: return False   # uAthena's old script parser has no '.@' scope vars -> won't compile
    if re.search(r'\bbonus\s+[A-Za-z_]\w*\s*;', sc): return False  # 1-arg flag bonus; uAthena bonus is "ii" (2 args)
    # strip script variables (any token bearing a sigil . $ ' # @ is a var name -> always ok)
    s = re.sub(r"[\$\.'#]*@?[A-Za-z_]\w*", lambda m: ' ' if re.match(r"[\$\.'#@]", m.group(0)) else m.group(0), sc)
    # validate quoted strings: in card scripts these are skill names -> must exist
    for q in re.findall(r'"([^"]*)"', sc):
        if q and q.upper() not in skills:
            return False
    # remove strings, then check bare identifiers
    s = re.sub(r'"[^"]*"', ' ', s)
    for ident in re.findall(r'[A-Za-z_]\w*', s):
        if ident.upper() not in KNOWN:
            return False
    return True

# ---- rAthena re: candidate mobs -> dropped (missing) card aegis ----------------
def parse_mob_drops(path):
    drops = set(); cur_id = None; mode = None
    for raw in open(path, encoding='utf-8', errors='replace'):
        if raw.startswith('#'): continue
        line = raw.rstrip('\n')
        mh = re.match(r'^  - Id:\s*(\d+)\s*$', line)
        if mh: cur_id = int(mh.group(1)); mode = None; continue
        if cur_id is None: continue
        if re.match(r'^    (Drops|MvpDrops):\s*$', line): mode = 'd'; continue
        if re.match(r'^    \w+:', line): mode = None; continue
        if mode == 'd':
            di = re.match(r'^      - Item:\s*(\S+)', line)
            if di: drops.add((cur_id, di.group(1).upper()))
    return drops

ua_mob = set()
for ln in open(f'{UA}/mob_db.txt', encoding='utf-8', errors='replace'):
    if ln.startswith('//'): continue
    m = re.match(r'\s*(\d+),', ln)
    if m: ua_mob.add(int(m.group(1)))

mob_drops = parse_mob_drops(f'{RA}/re/mob_db.yml')
need_aegis = {a for (mid, a) in mob_drops if mid not in ua_mob and a not in ua_item_aegis}

# ---- rAthena re cards (Type: Card) --------------------------------------------
LOC = {'Head_Low':1,'Right_Hand':2,'Garment':4,'Left_Accessory':8,'Armor':16,'Left_Hand':32,
       'Shoes':64,'Right_Accessory':128,'Head_Top':256,'Head_Mid':512,
       'Both_Hand':2|32,'Both_Accessory':8|128, 'Costume_Head_Top':256,'Costume_Head_Mid':512,
       'Costume_Head_Low':1,'Costume_Garment':4}

def parse_cards(path):
    items = {}; cur = None; sub = None; inscript = False; scr = []
    for raw in open(path, encoding='utf-8', errors='replace'):
        if raw.startswith('#'): continue
        line = raw.rstrip('\n')
        mh = re.match(r'^  - Id:\s*(\d+)', line)
        if mh:
            if cur is not None: cur['Script'] = '\n'.join(scr).strip()
            cur = {'Id': int(mh.group(1)), 'Locs': [], 'Script': ''}
            items[cur['Id']] = cur; sub = None; inscript = False; scr = []
            continue
        if cur is None: continue
        if inscript:
            if re.match(r'^    \w+:', line) or re.match(r'^  - Id:', line):
                inscript = False
            else:
                scr.append(line.strip()); continue
        f = re.match(r'^    (\w+):\s*(.*)$', line)
        if f:
            k, v = f.group(1), f.group(2).strip()
            if k == 'Script' and v == '|': inscript = True; scr = []
            elif k in ('Locations',): sub = 'loc'
            elif k in ('Flags','Trade','Jobs','Classes','Delay','AliasName'): sub = 'other'
            else: cur[k] = v; sub = None
            continue
        nm = re.match(r'^      (\w+):\s*(true|false)?', line)
        if nm and sub == 'loc' and (nm.group(2) in (None, 'true')):
            cur['Locs'].append(nm.group(1))
    if cur is not None: cur['Script'] = '\n'.join(scr).strip()
    return {v['AegisName'].upper(): v for v in items.values()
            if v.get('Type') == 'Card' and 'AegisName' in v}

cards = parse_cards(f'{RA}/re/item_db_etc.yml')

# ---- emit --------------------------------------------------------------------
def loc_mask(c):
    m = 0
    for l in c.get('Locs', []): m |= LOC.get(l, 0)
    return m

out, origs = [], []
st = dict(target=0, idconf=0, wrote=0, kept=0, emptied=0, noloc=0)
for a in sorted(need_aegis):
    if a not in cards: continue            # missing item is a card we don't have a def for? skip
    st['target'] += 1
    c = cards[a]
    iid = c['Id']
    if iid in ua_item_ids:                 # ID collision with an existing uAthena item -> skip+log
        st['idconf'] += 1
        origs.append(f"# ID-CONFLICT skip {iid} {c['AegisName']} (id already in uAthena)")
        continue
    name = (c.get('Name') or c['AegisName']).replace(',', ' ').replace('{','(').replace('}',')')
    buy  = c.get('Buy') or '20'
    weight = c.get('Weight') or '10'
    loc = loc_mask(c)
    if loc == 0: st['noloc'] += 1
    raw_sc = c.get('Script', '')
    if script_is_safe(raw_sc):
        body = ' '.join(x.strip() for x in raw_sc.splitlines() if x.strip())
        script = '{ %s }' % body if body else '{}'
        st['kept'] += 1
    else:
        script = '{}'
        st['emptied'] += 1
    if raw_sc:
        origs.append(f"{iid}\t{c['AegisName']}\t{'KEPT' if script!='{}' else 'DROPPED'}\t{' '.join(raw_sc.split())}")
    # ID,Aegis,Name,Type=6,Buy,Sell,Weight,ATK,DEF,Range,Slots,Job,Upper,Gender,Loc,wLV,eLV,Refine,View,{script},{},{}
    out.append(f"{iid},{c['AegisName']},{name},6,{buy},,{weight},,,,,,,,{loc},,,,,{script},{{}},{{}}")
    st['wrote'] += 1

open('/tmp/renewal_cards.txt', 'w', encoding='utf-8').write('\n'.join(out) + ('\n' if out else ''))
open('/tmp/renewal_card_scripts_orig.txt', 'w', encoding='utf-8').write('\n'.join(origs) + '\n')
print("CARDS: target_missing=%(target)d wrote=%(wrote)d  (script kept=%(kept)d emptied=%(emptied)d) "
      "id_conflicts_skipped=%(idconf)d  noloc=%(noloc)d" % st)
print(f"consts={len(consts)} buildins={len(buildins)} skills={len(skills)}")

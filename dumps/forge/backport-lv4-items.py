#!/usr/bin/env python3
# [Backport] Convert rAthena renewal weapon-level-4 weapons -> uAthena (eAthena) item_db
# CSV, for items NOT already in the repo. Rules (per request):
#   - EquipLevelMin > 99            -> capped to 99
#   - 3rd/4th class restriction     -> downgraded to 2nd job (Upper normal+upper)
#   - renewal job w/o pre-RE base   -> downgraded (Kagerou/Oboro->Ninja, Rebellion->Gunslinger)
#   - bonus scripts                 -> DROPPED (kept as plain weapons); rAthena scripts are
#                                      rAthena-syntax (EAJL_THIRD/bBaseAtk/RC_All... unknown to
#                                      uAthena) so they cannot be ported wholesale. The original
#                                      script is preserved in the reference file for manual porting.
# Source: /tmp/ra_equip.yml (rathena master db/re/item_db_equip.yml)
# Outputs: /tmp/lv4_items.txt (CSV lines) + /tmp/lv4_scripts_ref.txt (id<TAB>aegis<TAB>script)
import re

JOB_BIT = {
  'Novice':0x1,'SuperNovice':0x1,'Swordman':0x2,'Mage':0x4,'Archer':0x8,'Acolyte':0x10,
  'Merchant':0x20,'Thief':0x40,'Knight':0x80,'Priest':0x100,'Wizard':0x200,'Blacksmith':0x400,
  'Hunter':0x800,'Assassin':0x1000,'Crusader':0x4000,'Monk':0x8000,'Sage':0x10000,'Rogue':0x20000,
  'Alchemist':0x40000,'BardDancer':0x80000,'Taekwon':0x200000,'StarGladiator':0x400000,
  'SoulLinker':0x800000,'Gunslinger':0x1000000,'Ninja':0x2000000,
  # renewal jobs downgraded to their pre-RE base class
  'KagerouOboro':0x2000000,'Rebellion':0x1000000,
  # no pre-renewal equivalent (Doram) -> contributes nothing; see ALL fallback below
  'Summoner':0,'Spirit_Handler':0,
}
ALL_JOBS = 0xFFFFFFFF
SUBVIEW = {'Fist':0,'Dagger':1,'1hSword':2,'2hSword':3,'1hSpear':4,'2hSpear':5,'1hAxe':6,
  '2hAxe':7,'Mace':8,'Staff':10,'2hStaff':10,'Bow':11,'Knuckle':12,'Musical':13,'Whip':14,
  'Book':15,'Katar':16,'Revolver':17,'Rifle':18,'Gatling':19,'Shotgun':20,'Grenade':21,'Huuma':22}
GENDER = {'Female':0,'Male':1,'Both':2,'None':2}

def class_to_upper(classes):
    up = 0
    for c in classes:
        if   c == 'Third':       up |= 1   # 3rd normal  -> 2nd normal
        elif c == 'Third_Upper': up |= 2   # 3rd trans   -> 2nd trans
        elif c == 'Third_Baby':  up |= 4   # 3rd baby    -> 2nd baby
        elif c == 'All_Third':   up |= 7
        elif c == 'Fourth':      up |= 3   # 4th         -> 2nd normal+trans
        elif c == 'Upper':       up |= 2
        elif c == 'Normal':      up |= 1
        elif c == 'Baby':        up |= 4
        elif c == 'All':         up |= 7
    return up if up else 7

# repo item IDs (skip those already present)
repo_ids = set()
for ln in open('../../db/item_db.txt', encoding='utf-8', errors='replace'):
    m = re.match(r'\s*(\d+),', ln)
    if m: repo_ids.add(int(m.group(1)))

txt = open('/tmp/ra_equip.yml', encoding='utf-8', errors='replace').read()
blocks = txt.split('\n  - Id:')

def field(b, f):
    m = re.search(r'(?:^|\n)    ' + re.escape(f) + r':[ \t]*(.+)', b)
    return m.group(1).strip() if m else None

def submap(b, f):
    # nested map: "    F:\n      Name: true\n ..."
    m = re.search(r'(?:^|\n)    ' + re.escape(f) + r':[ \t]*\n((?:      \S.*\n)+)', b)
    out = []
    if m:
        for ln in m.group(1).splitlines():
            out.append(ln.strip().split(':')[0].strip())
    return out

def script_block(b):
    m = re.search(r'(?:^|\n)    Script:[ \t]*\|[ \t]*\n((?:      .*\n?)+)', b)
    if not m: return ''
    lines = [ln[6:] if ln.startswith('      ') else ln.strip() for ln in m.group(1).splitlines()]
    return ' '.join(s.strip() for s in lines if s.strip())

def san(s):
    # item names: strip commas (CSV delimiter) and braces
    return s.replace(',', ' ').replace('{', '(').replace('}', ')').strip() if s else ''

items, scripts = [], []
st = dict(total=0, skip=0, wrote=0, capped=0, downg=0, summ=0)
for b in blocks[1:]:
    b = 'Id:' + b
    mid = re.match(r'Id:[ \t]*(\d+)', b)
    if not mid: continue
    if field(b, 'WeaponLevel') != '4': continue
    st['total'] += 1
    iid = int(mid.group(1))
    if iid in repo_ids:
        st['skip'] += 1; continue

    aegis = field(b, 'AegisName') or ('Item_%d' % iid)
    name  = san(field(b, 'Name') or aegis)
    buy   = field(b, 'Buy') or ''
    sell  = field(b, 'Sell') or ''
    weight= field(b, 'Weight') or '0'
    atk   = field(b, 'Attack') or '0'
    df    = field(b, 'Defense') or '0'
    rng   = field(b, 'Range') or '0'
    slots = field(b, 'Slots') or '0'
    sub   = field(b, 'SubType') or ''
    view  = SUBVIEW.get(sub, 0)
    gen   = GENDER.get(field(b, 'Gender') or 'None', 2)

    jobs = submap(b, 'Jobs')
    if not jobs or 'All' in jobs:
        job = ALL_JOBS
    else:
        job = 0
        for j in jobs: job |= JOB_BIT.get(j, 0)
        if job == 0:           # only Doram/unknown jobs -> make broadly usable
            job = ALL_JOBS; st['summ'] += 1

    classes = submap(b, 'Classes')
    upper = class_to_upper(classes)
    if any(('Third' in c or 'Fourth' in c) for c in classes): st['downg'] += 1

    elv = int(field(b, 'EquipLevelMin') or '0')
    if elv > 99: elv = 99; st['capped'] += 1

    refine = field(b, 'Refineable')
    refine = '0' if (refine == 'false') else '1'

    # eAthena CSV: ID,Aegis,Name,Type,Buy,Sell,Weight,ATK,DEF,Range,Slots,Job,Upper,Gender,Loc,wLV,eLV,Refine,View,{},{},{}
    line = "%d,%s,%s,4,%s,%s,%s,%s,%s,%s,%s,0x%08X,%d,%d,2,4,%d,%s,%d,{},{},{}" % (
        iid, aegis, name, buy, sell, weight, atk, df, rng, slots, job, upper, gen, elv, refine, view)
    items.append(line)
    sc = script_block(b)
    if sc: scripts.append("%d\t%s\t%s" % (iid, aegis, sc))
    st['wrote'] += 1

open('/tmp/lv4_items.txt', 'w', encoding='utf-8').write('\n'.join(items) + '\n')
open('/tmp/lv4_scripts_ref.txt', 'w', encoding='utf-8').write('\n'.join(scripts) + '\n')
print("wLV4 total=%(total)d  skip_in_repo=%(skip)d  wrote=%(wrote)d  elv_capped=%(capped)d  class_downgraded=%(downg)d  doram_alljobs=%(summ)d" % st)

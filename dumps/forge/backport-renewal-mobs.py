#!/usr/bin/env python3
# [Backport] Renewal MOBS -> uAthena mob_db2 (eAthena CSV, 58 cols).
# Source: rAthena master commit 7f080871c8b3bbe7a79027194633201c63422ee1 (2026-06-18),
#         db/re/mob_db.yml  (the RE database -- renewal content lives only there).
# Rules (per request, "old rules", no new mechanics):
#   - additive: only mobs whose Id is NOT an uncommented entry in uAthena mob_db.txt.
#     Ids that ARE present but COMMENTED OUT in mob_db.txt are still added, but LOGGED.
#   - stats taken raw from RE, EXCEPT experience which is renewal-inflated (~x120/x72):
#         EXP  = round(BaseExp / EXP_DIV)      EXP_DIV = 120
#         JEXP = round(JobExp  / JEXP_DIV)     JEXP_DIV = 72
#         MEXP = round(MvpExp  / EXP_DIV)
#     (generation-time divisor, documented & tunable -- re-run to retune.)
#   - ATK2 synthesized: RE single-atk model has Attack2=0 -> ATK2 = Attack (flat dmg).
#   - Mode reconstructed (verified vs Baphomet 0x37B5):
#         mode = MONSTER_TYPE[Ai|06] | (Class==Boss ? MD_BOSS) | (Modes.Detector ? MD_DETECTOR)
#     renewal-only Modes (IgnoreMelee/Magic/.., StatusImmune, KnockBack, TeleportBlock, Mvp,
#     FixedItemDrop) have no uAthena bit -> dropped (no new mechanics). All values <= 0xFFFF.
#   - drops: AegisName -> uAthena item id (item_db.txt | item_db2.txt incl. backported cards).
#     card drop -> the card slot (Drop10 / str[56-57]); others -> Drop1..9; MvpDrops -> MVP1..3.
#     a drop whose item is missing in uAthena -> 0 + logged. rate scale identical (1/10000).
# Output: /tmp/renewal_mobs.txt (CSV)  +  /tmp/renewal_mobs_log.txt (conflicts / missing drops)
import re

UA = '/root/uAthena/db'
RA = '/tmp/rathena-ref/db'
EXP_DIV, JEXP_DIV, MEXP_DIV = 120, 72, 120
MAX_NORMAL_DROPS = 9   # Drop1..Drop9 ; slot 10 is the card slot

MD_BOSS, MD_DETECTOR = 0x20, 0x100
MONSTER_TYPE = {1:0x81,2:0x83,3:0x1089,4:0x3885,5:0x2085,6:0,7:0x108B,8:0x7085,9:0x3095,
    10:0x84,11:0x84,12:0x2085,13:0x308D,17:0x91,19:0x3095,20:0x3295,21:0x3695,24:0xA1,
    25:0x1,26:0xB695,27:0x8084}
AI_SPECIAL = {'ABR_PASSIVE':0x21,'ABR_OFFENSIVE':0xA5}
RACE = {'Formless':0,'Undead':1,'Brute':2,'Plant':3,'Insect':4,'Fish':5,'Demon':6,
    'Demihuman':7,'DemiHuman':7,'Angel':8,'Dragon':9,'Player_Human':7,'Player_Doram':7}
ELEM = {'Neutral':0,'Water':1,'Earth':2,'Fire':3,'Wind':4,'Poison':5,'Holy':6,'Dark':7,'Ghost':8,'Undead':9}
SIZE = {'Small':0,'Medium':1,'Large':2}

# ---- uAthena known sets ------------------------------------------------------
ua_mob_live, ua_mob_commented = set(), set()
for ln in open(f'{UA}/mob_db.txt', encoding='utf-8', errors='replace'):
    m = re.match(r'//(\d+),', ln)
    if m: ua_mob_commented.add(int(m.group(1))); continue
    m = re.match(r'\s*(\d+),', ln)
    if m and not ln.startswith('//'): ua_mob_live.add(int(m.group(1)))

ua_item_id = {}     # AEGIS_UPPER -> id
ua_card_aegis = set()
for fn in ('item_db.txt', 'item_db2.txt'):
    for ln in open(f'{UA}/{fn}', encoding='utf-8', errors='replace'):
        if ln.startswith('//') or ',' not in ln: continue
        p = ln.split(',')
        if len(p) < 4: continue
        try: iid = int(p[0])
        except: continue
        ag = p[1].strip().upper()
        ua_item_id[ag] = iid
        if p[3].strip() == '6': ua_card_aegis.add(ag)   # type 6 = card

# rAthena card aegis (so a drop is recognised as a card even if it landed in item_db2)
for raw in open(f'{RA}/re/item_db_etc.yml', encoding='utf-8', errors='replace'):
    pass  # cards already classified by uAthena type==6 above; rAthena set not needed for slotting

# ---- parse rAthena re mob_db.yml ---------------------------------------------
def parse_mobs(path):
    mobs = {}; cur = None; sub = None
    for raw in open(path, encoding='utf-8', errors='replace'):
        if raw.startswith('#'): continue
        line = raw.rstrip('\n')
        mh = re.match(r'^  - Id:\s*(\d+)\s*$', line)
        if mh:
            cur = {'Id': int(mh.group(1)), 'Drops': [], 'MvpDrops': [], 'Modes': set()}
            mobs[cur['Id']] = cur; sub = None; continue
        if cur is None: continue
        if re.match(r'^    Drops:\s*$', line): sub = 'drops'; continue
        if re.match(r'^    MvpDrops:\s*$', line): sub = 'mvp'; continue
        if re.match(r'^    Modes:\s*$', line): sub = 'modes'; continue
        f = re.match(r'^    (\w+):\s*(.*)$', line)
        if f:
            sub = None; cur[f.group(1)] = f.group(2).strip(); continue
        if sub in ('drops','mvp'):
            di = re.match(r'^      - Item:\s*(\S+)', line)
            if di:
                cur['Drops' if sub=='drops' else 'MvpDrops'].append([di.group(1).upper(), 0]); continue
            rr = re.match(r'^        Rate:\s*(\d+)', line)
            lst = cur['Drops' if sub=='drops' else 'MvpDrops']
            if rr and lst: lst[-1][1] = int(rr.group(1)); continue
        elif sub == 'modes':
            nm = re.match(r'^      (\w+):\s*(true|false)?', line)
            if nm and nm.group(2) in (None, 'true'): cur['Modes'].add(nm.group(1))
    return mobs

mobs = parse_mobs(f'{RA}/re/mob_db.yml')
cand = sorted(i for i in mobs if i not in ua_mob_live)

def I(m, k, d=0):
    try: return int(m.get(k, d))
    except: return d

def exp_scale(v, div):
    v = int(v)
    if v <= 0: return 0
    r = int(round(v / div))
    return r if r >= 1 else 1

def resolve(aegis):
    return ua_item_id.get(aegis.upper(), 0)

out, log = [], []
st = dict(wrote=0, commented=0, missdrop=0, trunc=0, no_ai=0, unk_race=0, over_cap=0)
miss_seen = set()

for mid in cand:
    m = mobs[mid]
    if mid > 10000:    # engine cap: MAX_MOB_DB=10000, mob_db_data[] index; ids 10001-30000 are the
        st['over_cap'] += 1   # size-variant display range -> server rejects ">10000". No engine change.
        log.append(f"OVER-MAXMOBDB\t{mid}\t{m.get('AegisName','?')}  (ID>10000 rejected by engine; not added)")
        continue
    if mid in ua_mob_commented:
        st['commented'] += 1
        log.append(f"COMMENTED-IN-UATHENA\t{mid}\t{m.get('AegisName','?')}  (was //{mid} in mob_db.txt; added anyway)")
    name = (m.get('Name') or m.get('AegisName','')).replace(',', ' ')
    name = re.sub(r'[^\x00-\x7F]+', '', name)           # ASCII-only (RO client codepage); strips e.g. greek Omega
    name = re.sub(r'\s+', ' ', name).strip() or m.get('AegisName', f'MOB_{mid}')
    sprite = m.get('AegisName', f'MOB_{mid}')
    lv  = I(m,'Level',1)
    hp  = I(m,'Hp',1); sp = I(m,'Sp',0)
    exp = exp_scale(I(m,'BaseExp'), EXP_DIV)
    jexp= exp_scale(I(m,'JobExp'), JEXP_DIV)
    r1  = I(m,'AttackRange',1)
    atk = I(m,'Attack',0); atk2r = I(m,'Attack2',0)
    atk2 = atk2r if atk2r > 0 else atk
    df  = I(m,'Defense',0); mdf = I(m,'MagicDefense',0)
    sstr= I(m,'Str',1); agi=I(m,'Agi',1); vit=I(m,'Vit',1); intl=I(m,'Int',1); dex=I(m,'Dex',1); luk=I(m,'Luk',1)
    r2  = I(m,'SkillRange',10); r3 = I(m,'ChaseRange',12)
    scale = SIZE.get(m.get('Size','Medium'), 1)
    rc = m.get('Race','Formless')
    if rc not in RACE: st['unk_race'] += 1; log.append(f"UNK-RACE\t{mid}\t{rc}")
    race = RACE.get(rc, 0)
    elv = I(m,'ElementLevel',1);  elv = 1 if elv<1 else (4 if elv>4 else elv)
    elem = elv*20 + ELEM.get(m.get('Element','Neutral'), 0)
    # mode
    ai = str(m.get('Ai','06')).strip()
    if 'Ai' not in m: st['no_ai'] += 1
    if ai.upper() in AI_SPECIAL: mode = AI_SPECIAL[ai.upper()]
    else:
        try: mode = MONSTER_TYPE.get(int(ai), 0)
        except: mode = 0
    if m.get('Class','Normal') == 'Boss': mode |= MD_BOSS
    if 'Detector' in m['Modes']: mode |= MD_DETECTOR
    speed = I(m,'WalkSpeed',200); adelay=I(m,'AttackDelay',1000); amotion=I(m,'AttackMotion',500); dmotion=I(m,'DamageMotion',500)
    mexp = exp_scale(I(m,'MvpExp'), MEXP_DIV)
    mexpper = 10000 if mexp > 0 else 0

    # ---- drops: split card vs normal; resolve ids ----
    card_id = card_per = 0
    normals = []
    for ag, rate in m['Drops']:
        iid = resolve(ag)
        if iid == 0:
            if ag not in miss_seen: miss_seen.add(ag); st['missdrop'] += 1
            log.append(f"MISS-DROP\t{mid}\t{ag}")
            continue
        if ag.upper() in ua_card_aegis and card_id == 0:
            card_id, card_per = iid, rate
        else:
            normals.append((iid, rate))
    if len(normals) > MAX_NORMAL_DROPS:
        st['trunc'] += 1; log.append(f"TRUNC-DROPS\t{mid}\t{len(normals)}>9")
        normals = normals[:MAX_NORMAL_DROPS]
    mvps = []
    for ag, rate in m['MvpDrops'][:3]:
        iid = resolve(ag)
        if iid: mvps.append((iid, rate))
        elif ag not in miss_seen:
            miss_seen.add(ag); st['missdrop'] += 1; log.append(f"MISS-MVPDROP\t{mid}\t{ag}")

    # ---- assemble 58 fields ----
    fields = [mid, sprite, name, name, lv, hp, sp, exp, jexp, r1, atk, atk2, df, mdf,
              sstr, agi, vit, intl, dex, luk, r2, r3, scale, race, elem, '0x%X'%mode,
              speed, adelay, amotion, dmotion, mexp, mexpper]
    for i in range(3):
        if i < len(mvps): fields += [mvps[i][0], mvps[i][1]]
        else: fields += [0, 0]
    for i in range(MAX_NORMAL_DROPS):
        if i < len(normals): fields += [normals[i][0], normals[i][1]]
        else: fields += [0, 0]
    fields += [card_id, card_per]
    out.append(','.join(str(x) for x in fields))
    st['wrote'] += 1

open('/tmp/renewal_mobs.txt', 'w', encoding='utf-8').write('\n'.join(out) + ('\n' if out else ''))
open('/tmp/renewal_mobs_log.txt', 'w', encoding='utf-8').write('\n'.join(log) + '\n')
st['cand'] = len(cand)
print("MOBS: candidates=%(cand)d wrote=%(wrote)d  over_MAX_MOB_DB(>10000,skipped)=%(over_cap)d  commented_id_conflicts=%(commented)d  "
      "distinct_missing_drop_items=%(missdrop)d  drop_truncations=%(trunc)d  no_Ai(->mode by 06)=%(no_ai)d  unknown_race=%(unk_race)d"
      % st)
# field-count sanity
bad = [l for l in out if l.count(',') != 57]
print(f"field-count check: lines={len(out)}  wrong_width={len(bad)}")

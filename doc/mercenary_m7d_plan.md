# План: Mercenary Soldier M7d — поведение скиллов + AI-каст

**Контекст:** наёмники призываются/дерутся (melee + кастомный AI follow/aggro/chase из M7c), скиллы
8201-8240 определены в skill_db + remap'нуты, но **поведение не подключено** (0 merc-case в skill.c/
battle.c, 0 set_sc в status.c). Предыдущее: [[mercenary-soldier-port-deferred]] (memory). M7d = последняя
часть. Согласовано «делать сейчас» (2026-06-16). Эталон: `/tmp/eathena-ref` (`/bin/grep`).

## КЛЮЧЕВАЯ НАХОДКА (разведка)
**У eAthena наёмников НЕТ автономного AI/скилл-каста** — всё player-driven через clif-команды
(`clif_parse_UseSkillToId_mercenary`). Под нашим PV7 merc-окна нет (`#if PACKETVER>=20080102` дормант)
→ **кастовать скиллы может ТОЛЬКО наш кастомный AI**. Значит M7d состоит из двух частей:
- **Механика 40 скиллов** — портируется из eAthena: добавить merc-`case` рядом с зеркальным player-case
  в switch'ах skill.c/battle.c + маппинги status.c. Механически, но в ГОРЯЧЕМ коде, непроверяемо здесь.
- **AI-каст** — С НУЛЯ (в eAthena нет), поверх существующего `merc_ai_sub_hard`.

Текущее: `mercenary_killbonus` зовёт `status_change_start(SC_MERC_*)`, но обработчиков SC_MERC_* в
status.c нет → баф без эффекта (чинится в M7d-1).

---

## Merc→player карта (ПОЛНАЯ, из разведки эталона)

### skill.c — `skill_castend_damage_id` (офенс, группа с player-case)
MS_BASH↔SM_BASH; MS_MAGNUM↔SM_MAGNUM (+merc-ветка: SC_WATK_ELEMENT + `if(BL_MER) skill_blockmerc_start`);
MS_BOWLINGBASH↔KN_BOWLINGBASH; MA_DOUBLE↔AC_DOUBLE; MA_SHOWER↔AC_SHOWER; MA_CHARGEARROW↔AC_CHARGEARROW;
MA_SHARPSHOOTING↔SN_SHARPSHOOTING; ML_PIERCE↔KN_PIERCE; ML_BRANDISH↔KN_BRANDISHSPEAR (+nodamage_id 3946→
skill_brandishspear); ML_SPIRALPIERCE↔LK_SPIRALPIERCE; MER_CRASH=в группе SM_BASH/MS_BASH.

### skill.c — `skill_castend_nodamage_id` (бафы/тогглы/саппорт)
Generic buff-block (sc_start 100%): MS_PARRYING↔LK_PARRYING, MS_REFLECTSHIELD↔CR_REFLECTSHIELD,
MS_BERSERK↔LK_BERSERK, MER_QUICKEN(↔KN_TWOHANDQUICKEN group). MER_SIGHT↔MG_SIGHT; MER_DECAGI↔AL_DECAGI;
MER_LEXDIVINA↔PR_LEXDIVINA (toggle); MER_KYRIE↔PR_KYRIE; MER_INCAGI↔AL_INCAGI; MER_BLESSING↔AL_BLESSING
(+MER_BLESSING/INCAGI head-ветка: target SC_CHANGEUNDEAD→skill_attack BF_MISC); MER_PROVOKE↔SM_PROVOKE
(+`if(dstmd) mob_target`); MER_AUTOBERSERK↔SM_AUTOBERSERK (toggle); ML_DEFENDER↔CR_DEFENDER,
ML_AUTOGUARD↔CR_AUTOGUARD (toggle on/off); ML_DEVOTION↔CR_DEVOTION (+merc-ветка: только владелец);
MER_MAGNIFICAT (standalone: self + party/master); MA_REMOVETRAP↔HT_REMOVETRAP (+BL_MER снимает любую).
Standalone-cure: MER_REGAIN(sleep+stun), MER_TENDER(freeze+stone), MER_BENEDICTION(curse+blind),
MER_RECUPERATE(poison+silence), MER_MENTALCURE(confusion), MER_COMPRESS(bleeding), MER_SCAPEGOAT
(heal master по HP мерка→kill merc), MER_ESTIMATION(`sd=mer->master`→fallthrough WZ_ESTIMATION).

### skill.c — прочее
`skill_get_range2`: MA_SHOWER 237/MA_DOUBLE 238/MA_CHARGEARROW 241 (+AC_VULTURE). `skill_castend_pos2`:
MA_SKIDTRAP/LANDMINE/SANDMAN/FREEZINGTRAP (ставят UNT_* как HT_), MA_SHOWER (ground). `skill_unitsetting`:
4 trap-таймера + val1=3500. `skill_check_unit_range_sub`: 4 trap (stacking). `skill_additional_effect`:
MER_CRASH→SC_STUN(6*lv); MA_FREEZINGTRAP→SC_FREEZE(3*lv+35); MA_LANDMINE→SC_STUN(5*lv+30); MA_SANDMAN→
SC_SLEEP(10*lv+40); ML_SPIRALPIERCE→SC_STOP(15+lv*5). `skill_check_condition_castbegin`+`skill_get_requirement`:
ML_AUTOGUARD/ML_DEFENDER turn-off check. Merc-требования (HP/SP/item) — через `skill_check_condition_mercenary`
(уже есть? проверить) для BL_MER||BL_HOM, не player-castbegin/castend.

### battle.c — `battle_calc_weapon_attack` (hit / skillratio)
hit: MS_BASH↔SM_BASH(+5%/lv); MS_MAGNUM↔SM_MAGNUM(+10%/lv); ML_PIERCE↔KN_PIERCE(div_=size+1,+5%/lv);
MA_SHARPSHOOTING↔SN_SHARPSHOOTING(cri+200); MS_BOWLINGBASH↔KN_BOWLINGBASH(blewcount=0);
ML_SPIRALPIERCE↔LK_SPIRALPIERCE (weight-block). skillratio: MS_BASH(+30*lv), MS_MAGNUM(+20*lv),
MA_DOUBLE(+10*(lv-1)), MA_SHOWER(+5*lv-25), MA_CHARGEARROW(+50), MA_FREEZINGTRAP(↔HT, -50+10*lv),
ML_PIERCE(+10*lv), MER_CRASH(standalone +10*lv), ML_BRANDISH(↔KN_BRANDISHSPEAR), MS_BOWLINGBASH(+40*lv),
MA_SHARPSHOOTING(+100+50*lv). +2 не-case условия: crit-gate `||MA_SHARPSHOOTING` (~1147), SC-skip
`&& skill!=ML_SPIRALPIERCE` (~1905). `battle_calc_misc_attack`: MA_LANDMINE↔HT_LANDMINE. `battle_check_target`:
MA_REMOVETRAP↔HT_REMOVETRAP, MA_SHOWER/MS_MAGNUM (могут бить trap).

### status.c — `initChangeTables` set_sc/add_sc (21 строка)
add_sc: MER_CRASH→SC_STUN, MS_MAGNUM→SC_WATK_ELEMENT, MER_SIGHT→SC_SIGHT, MER_LEXDIVINA→SC_SILENCE,
MA_LANDMINE→SC_STUN, MA_SANDMAN→SC_SLEEP, MA_FREEZINGTRAP→SC_FREEZE, ML_SPIRALPIERCE→SC_STOP,
ML_DEVOTION→SC_DEVOTION. set_sc (icon+SCB): MER_PROVOKE→SC_PROVOKE, MER_DECAGI→SC_DECREASEAGI,
MER_MAGNIFICAT→SC_MAGNIFICAT, MER_AUTOBERSERK→SC_AUTOBERSERK, ML_AUTOGUARD→SC_AUTOGUARD,
MS_REFLECTSHIELD→SC_REFLECTSHIELD, ML_DEFENDER→SC_DEFENDER, MS_PARRYING→SC_PARRYING, MS_BERSERK→SC_BERSERK,
MER_QUICKEN→SC_MERC_QUICKEN(SCB_ASPD), MER_KYRIE→SC_KYRIE, MER_BLESSING→SC_BLESSING, MER_INCAGI→SC_INCREASEAGI.
(Все player-SC уже работают; merc-специфичен только SC_MERC_QUICKEN.)

### status.c — 6 SC_MERC_* обработчики (нужны; killbonus их стартует, эффекта нет)
SC_MERC_FLEEUP→status_calc_flee +15*val1 (SCB_FLEE); ATKUP→watk +15*val1 (SCB_WATK); HPUP→maxhp
+maxhp*5*val1/100 (SCB_MAXHP, heal на end); SPUP→maxsp аналогично (SCB_MAXSP); HITUP→hit +15*val1
(SCB_HIT); QUICKEN→aspd +val2=300 (SCB_ASPD, OPT3_QUICKEN, конфликт с DECREASEAGI/QUAGMIRE).
+ status_change_start: val2-формулы + BL_MER-гейт для 5 kill-бонусов.

### Merc-специфичные ветки (8) — портировать аккуратно
MS_MAGNUM (BL_MER→SC_WATK_ELEMENT+blockmerc); MA_REMOVETRAP (BL_MER снимает любой trap); ML_DEVOTION
(только master); MER_MAGNIFICAT (mer→self+party/master); MER_PROVOKE (dstmd→mob_target); MER_SCAPEGOAT
(mer→master heal+self-kill); MER_ESTIMATION (sd=mer->master fallthrough); MER_BLESSING/INCAGI
(SC_CHANGEUNDEAD head). MA_REMOVETRAP range — по позиции МАСТЕРА (unit.c).

---

## Фазы (каждая: build clean + commit + отчёт; fetch+rebase перед push — Cline Bot)

- **M7d-1 (статус-фундамент):** status.c — 21 set_sc/add_sc в initChangeTables + 6 SC_MERC_* обработчики
  (status_calc_flee/watk/maxhp/maxsp/hit/aspd + SCB-флаги + status_change_start val2/BL_MER-гейт).
  Делает kill-бонус рабочим + готовит SC для бафф-скиллов. Низко-средний риск (таблицы + status_calc).
- **M7d-2 (офенс-урон):** skill_castend_damage_id + battle.c (hit/skillratio/misc/check_target) +
  skill_get_range2 + 2 условия. ~11 офенс-скиллов. Горячо; ценно (мерк бьёт скиллами).
- **M7d-3 (бафы/тогглы/саппорт):** skill_castend_nodamage_id (бафы, toggle, cure, devotion, provoke,
  magnificat, estimation, scapegoat) + castbegin/get_requirement toggle-check + merc-ветки.
- **M7d-4 (ловушки):** MA_*TRAP — skill_castend_pos2 + skill_unitsetting + check_unit_range_sub +
  skill_additional_effect SC (триггер/урон переиспользуют HT_ UNT_ пути).
- **M7d-5 (AI-каст, С НУЛЯ):** merc_ai_sub_hard — на спавне активировать пассивы/бафы (REFLECTSHIELD/
  PARRYING/AUTOGUARD/DEFENDER/QUICKEN по классу через mercenary_checkskill); в бою вероятностный
  офенс-каст (unit_skilluse_id ближайшего скилла из списка, проверка SP/cooldown). Использовать
  `mercenary_checkskill` + `skill_get_sp`. Опц.: support-мерк хилит/бафает мастера.
- **M7d-6 (опц.):** merc-guild NPC-скрипты (наём/вера) — после.

## Проверка/риск
Build clean (make sql, 0 новых ворнингов) на каждой фазе. Runtime (спавн/бой/скиллы/relog) =
ТЕСТИРОВЩИКИ (нужен клиент; здесь карты/мобы без char-сервера не грузятся). Горячий код — сверять
каждую merc-`case` с эталоном; merc-ветки не пропускать. Отчёт `doc/mercenary_soldier_changes.md`
(дописывать M7d-секции). GNUmakefile генерится из Makefile.

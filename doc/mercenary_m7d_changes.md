# Mercenary M7d — изменения для тестировщиков

Подключение поведения merc-скиллов (8201-8240) поверх готового ядра наёмников (призыв/бой/AI/`@merc`).
План + полная карта порта: `doc/mercenary_m7d_plan.md`. Реализуется по фазам.

**Контекст:** у eAthena наёмники кастуют скиллы только по команде клиента, а под нашим PV7 merc-окна нет
→ скиллы будет кастовать наш кастомный AI (фаза M7d-5). Механика скиллов (фазы 1-4) подключается заранее.
Runtime-проверка (нужен клиент + кластер) — на тестировщиках.

---

## Фаза M7d-1 — Статус-фундамент (СДЕЛАНО)

**Что изменилось:**
- `src/map/skill.h` — добавлены enum-константы MER_* (8222-8240: MAGNIFICAT/QUICKEN/SIGHT/CRASH/REGAIN/
  TENDER/BENEDICTION/RECUPERATE/MENTALCURE/COMPRESS/PROVOKE/AUTOBERSERK/DECAGI/SCAPEGOAT/LEXDIVINA/
  ESTIMATION/KYRIE/BLESSING/INCAGI). Раньше были только MS_/MA_/ML_ (8201-8221).
- `src/map/status.c` `initChangeTables` — 21 маппинг merc-скилл→status-change (set_sc/add_sc), как в
  eAthena. Player-SC (SC_BERSERK/PROVOKE/AUTOGUARD/REFLECTSHIELD/DEFENDER/…) переиспользуют существующую
  логику. Иконки SI_MERC_* НЕ добавлялись (под PV7 косметика, не рисуются).
- `src/map/status.c` — **kill-bonus теперь рабочий**: 6 обработчиков SC_MERC_* (ранее `mercenary_killbonus`
  стартовал баф, но эффекта не было): FLEEUP→flee, ATKUP→watk, HITUP→hit (+15·tier); HPUP→maxhp, SPUP→maxsp
  (+5%·tier); QUICKEN→aspd. SCB-флаги + val2-расчёт (status_change_start) + BL_MER-гейт (баффы только для
  наёмников) + полный heal HP/SP при выдаче HPUP/SPUP.

**Что отложено** (дормант, пока скиллы некастуемы — включится в M7d-3/5): QUICKEN opt3/eligibility/cancel.

**Эффект для игры:** каждые 50 убийств наёмник получает случайный баф (FLEE/ATK/HP/SP/HIT, ~10 мин) —
теперь реально повышает стат (раньше был no-op). Прочие маппинги активируются, когда скиллы начнут
кастоваться (M7d-2/3 механика + M7d-5 AI).

**Верификация (здесь):** `make sql` EXIT=0, 0 новых ворнингов, бинарники линкуются. Геймплейная
проверка (наёмник на 50-м килле получает стат-баф) — на тестировщиках.

**Откат:** реверт коммита фазы.

## Фаза M7d-2 — Офенсивный урон (СДЕЛАНО)

Подключены 11 атакующих merc-скиллов — каждый сгруппирован рядом с зеркальным player-скиллом
(общий обработчик), точно по эталону eAthena.

**Что изменилось:**
- `src/map/skill.c` `skill_castend_damage_id` — merc-метки добавлены к телам player-скиллов:
  MS_BASH/MER_CRASH/MA_DOUBLE/ML_PIERCE/MA_CHARGEARROW/ML_SPIRALPIERCE (общее weapon-тело),
  MS_MAGNUM/MA_SHOWER (splash-тело), MA_SHARPSHOOTING (line-attack), ML_BRANDISH, MS_BOWLINGBASH.
  MS_MAGNUM теперь тоже даёт fire-element баф (расширен guard SC_WATK_ELEMENT). `skill_get_range2` —
  MA_SHOWER/DOUBLE/CHARGEARROW получают range-бонус AC_VULTURE.
- `src/map/battle.c` `battle_calc_weapon_attack` — урон/хит/крит merc-скиллов = как у зеркал:
  hit (MS_BASH +5%·lv, MS_MAGNUM +10%·lv, ML_PIERCE +5%·lv), div_ (ML_PIERCE = size+1), blewcount=0
  (MS_BOWLINGBASH), вес-урон (ML_SPIRALPIERCE → atk2 для не-игрока), крит (MA_SHARPSHOOTING +200),
  skillratio (MS_BASH +30·lv, MS_MAGNUM +20·lv, MA_DOUBLE +10·(lv-1), MA_SHOWER +5·lv-25,
  MA_CHARGEARROW +50, ML_PIERCE +10·lv, MER_CRASH +10·lv, ML_BRANDISH, MS_BOWLINGBASH +40·lv,
  MA_SHARPSHOOTING). +SC-скип для ML_SPIRALPIERCE.

**Решения (по флагам спеки):**
- MS_MAGNUM merc-кулдаун НЕ портирован (uAthena `skill_blockmerc_start` — для homun, не для Mercenary
  Soldier; eAthena к тому же привязывал его к цели — баг). Применён только fire-element баф.
- MA_SHARPSHOOTING наследует **uAthena**-формулу skillratio (`50·lv`), а не eAthena (`100+50·lv`) —
  для консистентности с уже существующим player-Снайпером (player-формулу НЕ трогаем).

**Верификация (здесь):** `make sql` EXIT=0, 0 новых ворнингов. Урон merc-скиллов проверяется только
в бою с клиентом → **на тестировщиках** (и активируется, когда AI начнёт кастовать — M7d-5).

**Откат:** реверт коммита фазы.

## Фаза M7d-3a — Боевые бафы/дебафы/тогглы (СДЕЛАНО)

13 self-баф/дебаф merc-скиллов, которые реально кастует combat-AI, подключены к зеркальным
player-обработчикам в `skill_castend_nodamage_id`.

**Что изменилось (`src/map/skill.c`):**
- Generic buff-блок (общее sc_start-тело): **MS_BERSERK** (=LK_BERSERK), **MER_QUICKEN**
  (=KN_TWOHANDQUICKEN), **MS_REFLECTSHIELD** (=CR_REFLECTSHIELD), **MS_PARRYING** (=LK_PARRYING),
  **MER_INCAGI** (=AL_INCAGI), **MER_BLESSING** (=AL_BLESSING).
- **MER_SIGHT** (=MG_SIGHT), **MER_DECAGI** (=AL_DECAGI), **MER_LEXDIVINA** (=PR_LEXDIVINA toggle),
  **MER_PROVOKE** (=SM_PROVOKE, с dstmd→mob_target), **MER_AUTOBERSERK** (=SM_AUTOBERSERK toggle),
  **ML_DEFENDER/ML_AUTOGUARD** (=CR_DEFENDER/CR_AUTOGUARD on/off-toggle) + их turn-off-проверка в
  `skill_check_condition`.
- `src/map/status.c` — SC_MERC_QUICKEN `val2=300` (даёт +300 aspd-rate, как Two-Hand Quicken).

**Решения:** undead-ветка MER_BLESSING/INCAGI (бьёт нежить) **пропущена** (refinement, не меняем
AL_-поведение, нет зависимости от SC_CHANGEUNDEAD). MS_BERSERK = LK_BERSERk (HP-based berserk) как в
eAthena. Все merc-case'ы садятся на sd-безопасные тела (нет деref-краша для не-игрока).

**Отложено в M7d-5** (дормант под PV7 / edge): QUICKEN opt3-визуал + DECREASEAGI-конфликт +
cancel-on-berserk/dontforgetme.

**Верификация:** `make sql` EXIT=0, 0 новых ворнингов. Активируется, когда AI начнёт кастовать (M7d-5).

**Откат:** реверт коммита фазы.

## Фаза M7d-5 — Кастомный AI-каст офенс-скиллов (KEYSTONE, СДЕЛАНО)

**Это спусковой крючок:** до этой фазы вся механика M7d-1/2/3a была дормант (под PV7 нет merc-окна,
никто скиллы не кастовал). Теперь кастомный merc-AI сам применяет атакующие скиллы в бою.

**Что изменилось:**
- `src/map/mercenary_soldier.c` — хелпер `merc_attack_skill()`: из списка скиллов наёмника
  (`mercenary_skill_db`) выбирает случайный атакующий (`INF_ATTACK_SKILL`) и кастует в цель через
  `unit_skilluse_id`. Интегрирован в `merc_ai_sub_hard`: в бою, в радиусе цели, с шансом
  `merc_skill_rate` наёмник кастует скилл вместо обычной атаки (при неудаче — обычный melee).
- `battle_config merc_skill_rate` (battle.h/battle.c/`conf/battle/monster.conf`) — шанс % (default **30**,
  0 = отключить merc-скиллы).

**Поведение:** `unit_skilluse_id` для BL_MER безопасен (player/SP-проверки в нём sd-only → пропускаются;
наёмник кастует **без расхода SP**, как моб). Время каста + AI-гейт не дают спамить. Эффект скилла даёт
`skill_castend` (merc-case'ы из M7d-2). Итог: наёмник в бою чередует melee и атакующие скиллы (BASH/
MAGNUM/BOWLINGBASH/DOUBLE/SHOWER/PIERCE/BRANDISH/SPIRALPIERCE/SHARPSHOOTING/CHARGEARROW по своему классу).

**Пока НЕ кастует AI** (отдельные фазы): self-бафы M7d-3a (нужен M7d-5b — активация на спавне/idle),
саппорт/cure/devotion на мастера (M7d-3b), ловушки (M7d-4).

**Верификация:** `make sql` EXIT=0, 0 новых ворнингов. **Runtime (наёмник реально кастует скиллы в бою,
анимации/урон/баланс) — на тестировщиках** (нужен клиент + кластер). Тюнинг — `merc_skill_rate`.

**Откат:** `merc_skill_rate: 0` (без пересборки) или реверт коммита.

<!-- M7d-5b (self-бафы на спавне), M7d-3b (саппорт/cure/devotion), M7d-4 (ловушки) — далее. -->

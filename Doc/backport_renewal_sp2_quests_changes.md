# SP-2 Renewal quests (2-pre + 2a) — изменения

Источник: rAthena `7f08087`. Ветка x64. Под-проект 2 роадмапа. Переиспользует SP-1/SP-3.

## 2-pre — quest_db-добор + engine split (commit 5cdb893)

- `db/quest_db.txt`: 1703 → 2776 (+1073 renewal quest-ID). Конвертер
  `dumps/forge/backport-renewal-questdb.py` (yml→TXT 9-field, mob aegis→id, ≤3 targets;
  119 target-drops логированы `Doc/backport_renewal_questdb_drops.txt`).
- **ENGINE-правка** (разделение перегруженного MAX_QUEST_DB): `MAX_QUEST_DB`=2000→**3000**
  (глобальный `quest_db[]`) + новый **`MAX_PC_QUESTS`=500** (per-char `quest_log[]`/
  `quest_index[]`/int_quest.c). Per-char memory ПАДАЕТ (48KB→12KB/сессию), db-cap растёт.
  Файлы: mmo.h, map.h, quest.c, int_quest.c. Boot: «Done reading 2776 entries», 0 errors.

## 2a — zone-quests (7 файлов)

`npc/backport/re_quests/` (eclage/malangdo/malaya/dicastes/rockridge/mora/dewata). Генератор
`dumps/forge/backport-renewal-quests.py` (собран town adapt_text + merchant block_filter +
quest tail). События: ADAPT 573, COMMENT 1034, BOUNDARY 307, DEDUP, UNRESOLVED 75, ORPHAN.

## Улучшения общего генератора (выигрывают все фазы; merchant/smallnpc re-gen)

- **userfunc→callfunc** (quest gen): uAthena не поддерживает прямой paren-call к script-
  функциям (`unknown_d(a,b)` → `callfunc("unknown_d",a,b)`); `function script Name` собираются,
  их вызовы переписываются. Исправило 50 dicastes-ошибок.
- **block_filter BROKEN +multiline-args** (`\w+(...,$`): ловит многострочные `= callfunc("F_X",`
  (adven_boards F_AvenBoard). Добавлено в общий block_filter (merchant/smallnpc re-gen 0 регрессии).
- **existing_npc_index scope** → исключает ВСЕ `/backport/re_` (дедуп против ядра uAthena +
  pre-renewal backport, НЕ против renewal-серии) — убрало self-DEDUP при re-gen (quest 414→0).

## Верификация

- Конвертер + генератор `--selftest`/`--verify` OK. Финальный boot `--run_once`: **0 total
  script errors**, все re_* (quests/merchants/other) чисто, quest_db 2776, 16484 NPC, Server ready.
- 1 deploy-artifact (itemmall .gat, прод OK).

## За тестерами

Достижимость квестов, цепочки/диалоги, баланс наград, `.gat` зон. dropped renewal-feature
квесты (clear/sit/delequip/mesitemlink/questinfo) + F_GM_NPC/F_Malaya_Nurse — для будущего
движкового/Global_Functions порта. SP-2 2b/2c/2d (eden/dungeon-collection/simple) — следующие
под-фазы на том же фундаменте (quest_db + генератор).

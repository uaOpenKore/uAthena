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

## 2b — Eden Group quests (16 файлов)

`npc/backport/re_eden/` (eden_common/service/tutorial/quests/iro + 11 board/level-файлов
11-25..eden_131_140). Генератор `dumps/forge/backport-renewal-eden.py` (копия quests-генератора,
сменён только tail: OUT_DIR=re_eden, file-list EDEN_FILES, HEADER, includes/maps/gap-имена).
13501 строк rAthena → 16 файлов. События: ADAPT 240, COMMENT 98, UNRESOLVED 36, MANUAL 10,
BOUNDARY 7, SITEFIX 3, DEDUP 2. Подключены в `npc/scripts_athena.conf` (блок «2b»). VERIFY OK,
boot чист (0 ошибок по re_eden). `F_GM_NPC` (2 вызова в eden_quests) — informational runtime-ref
(renewal Global_Function, как F_GM_NPC/F_Malaya_Nurse в 2a; не parse-ошибка).

## ДВИЖКОВЫЙ ФИКС парсера комментариев (вскрыто на 2b, чинит ВСЕ фазы)

`src/map/npc.c` `npc_parsesrcfile`: проверка строки-комментария `//` срабатывала только в
колонке 0 (`line[0]=='/' && line[1]=='/'`). Сгенерированные закомментированные строки скрипта,
сохраняющие ведущий отступ (`\t//[BACKPORT-GAP:...]`), парсились как NPC-определения → спам
`Invalid map '//...'` (1956 ошибок по всем re_* фазам). Фикс: стрипнуть ведущие пробелы/табы
перед проверкой `//` (рядом уже был такой whitespace-стрип для `/* */`). Нужен `make sql`.
Результат: 1956 → 0 `Invalid map`. **Это вторая engine-правка серии** (после quest_db split) —
bugfix парсера, не игровая механика.

## ВАЖНО: критерий верификации расширен (находка 2b)

Прошлые boot-проверки фаз грепали класс `script error`; класс `Invalid map`/`Could not parse`
не проверялся → 1956 indented-comment ошибок (выше) и **9 реальных parse-ошибок в SP-3
`global_npcs.txt`** жили незамеченными. Теперь критерий = `[Error]` минус известные не-parse
классы (grfio `.gat`/`.rsw`, viewdata renewal-спрайтов, `bad duplicate ... #it01` itemmall
deploy-артефакт, опциональный `PCLoginEvent.txt`, runtime OnInit). После всех фиксов финальный
boot: 0 `Invalid map`/`Could not parse`/`unknown buildin`, 16541 NPC.

## SP-3 доработка: NPC display-state `script(FLAG)` (вскрыто 2b-верификацией)

`global_npcs.txt` (SP-3) содержал renewal-синтаксис `-\tscript(CLOAKED|DISABLED|HIDDEN)\t...`
(display-state определения), которого нет в парсере uAthena → `Could not parse` (9 строк, ровно
1 файл/1 паттерн на всю серию). Общее правило в adapt_text (town-npcs.py + smallnpc.py):
`\tscript(\w+)\t` → `\tscript\t` (drop state; renewal-косметика, dummy-шаблоны и так sprite -1).
SP-3 регенерирован (`backport-renewal-smallnpc.py`): diff = ровно 3 строки, +13 NPC ожили.

## 2c — dungeon/collection quests (8 файлов)

`npc/backport/re_collections/` (magic_books, homun_s, illusion_investigation,
quests_illusion_dungeons, juno_monster_society, garden_of_time, quests_dungeons_200,
HelpMeShorty). ~25K строк rAthena. Генератор `dumps/forge/backport-renewal-collections.py`
(клон eden-генератора, сменён только tail: OUT_DIR=re_collections, COLLECTION_FILES,
`npc/re/quests/{n}` без eden/, selftest==8). Подключены в scripts_athena.conf «2c».
VERIFY OK (unresolved refs: none). boot parse-чист, 16546 NPC.
События: ADAPT 525, COMMENT 1143, BOUNDARY 282, UNRESOLVED 49, ORPHAN 24, MANUAL 180.

## НАХОДКА: NAME_LENGTH=24 ломает duplicate с длинным base-именем (кросс-фазное)

`src/common/mmo.h NAME_LENGTH 24` (23 символа + null). NPC-имя длиннее обрезается при
регистрации, а `duplicate(полное_имя)` ищет необрезанное → `bad duplicate name (not exist)`.
Реально ломает (полный boot): `Carbonated Water Vending Machine#ra` (juno, ×6 городов-duplicate)
+ `Equipment Reform PR Agent#it01` (re_merchants, ×1) = **7 NPC**. ВАЖНО: ранее `#it01`
списывался на «itemmall deploy-артефакт» — НЕВЕРНО, это NAME_LENGTH-обрезка, на проде та же.
Большинство длинных имён (167 ≥24) РАБОТАЮТ (single-NPC обрезается лишь в display; duplicate-пары
обрезаются согласованно). Не parse-ошибка, boot не блокирует. Стратегия (engine ↑NAME_LENGTH
рискованно для wire/DB / генератор-укорачивание / оставить+документировать) — решается отдельно.

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

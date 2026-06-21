# SP-2 Design: бэкпорт renewal-квестов (decompose + 2-pre quest_db + 2a zone-quests)

Статус: ДИЗАЙН СОГЛАСОВАН (brainstorming). Под-проект 2 роадмапа
`Doc/backport_renewal_content_roadmap.md` (порядок 1→3→2; SP-2 последний). Ветка x64.
0 правок движка. Источник rAthena `7f08087`. Переиспускает активы SP-1/SP-3
([[backport-renewal-content-series]]).

## Цель и декомпозиция

Бэкпортировать renewal-квесты (~100K строк, 49 IN-файлов). Дробится на **2-pre (фундамент)
+ 4 под-фазы**, каждая свой spec→plan→impl:

- **2-pre — quest_db-добор**: 1073 renewal quest-ID → `db/quest_db.txt` (без них `setquest`
  даёт warning во всех под-фазах). Этот spec покрывает 2-pre + 2a.
- **2a — zone-quests** (~59K): eclage, malangdo, malaya, dicastes, rockridge, mora, dewata.
- **2b — eden** (~13.5K): 16 файлов Eden Group. (отдельный spec позже)
- **2c — dungeon/collection** (~25K): illusion_dungeons, juno_monster_society, garden_of_time,
  homun_s, magic_books, dungeons_200, HelpMeShorty. (отдельный spec позже)
- **2d — simple** (~2K): ninja_quests, cupet, cooking, pile_bunker, mrsmile, простые town.
  (отдельный spec позже)

**OUT**: эпизоды 14.3-18 (9 файлов, 64.6K, instance-gated — нет `instance.c`).

## 2-pre — quest_db-добор (1073 quest-ID)

- **Цель**: `db/quest_db.txt` (append; сейчас 1703 ID → ~2776). Формат старый eAthena:
  `Quest_ID,Time_Limit,Target1,Val1,Target2,Val2,Target3,Val3,"Quest_Title"` (9 полей, до 3
  mob-целей).
- **Источник**: rAthena `db/re/quest_db.yml` (1073 = из 1075 missing, 2 не в yml). Поля:
  `Id`→ID, `Title`→title, `TimeLimit`→Time, `Targets[].Mob/Count`→Target/Val (до 3; лишние
  цели drop+log).
- **Конвертер** `dumps/forge/backport-renewal-questdb.py` (yml→TXT, база как item-конвертер
  SP-1a). Только missing-ID (не в uAthena quest_db). ID-конфликтов нет (строго missing).
- **Объём**: 1073 quest-ID охватывают ВСЕ SP-2 под-фазы (2a-2d) — добор один раз, фундамент.
- Boot quest_db-load: 0 parse-errors на доборенных ID.

## 2a — zone-quests (7 файлов, ~59K)

- **Вход**: `npc/re/quests/quests_{eclage,malangdo,malaya,dicastes,rockridge,mora,dewata}.txt`.
  Зоны уже портированы (warps/town/merchants/small-NPC фазы) → квесты ложатся на готовые карты.
- **Вывод**: `npc/backport/re_quests/`.
- **Генератор** `dumps/forge/backport-renewal-quests.py` — тот же зрелый паттерн (собран из
  town `adapt_text` 12+ классов + merchant `block_filter`/orphan/existing-index, как SP-3).
  Переиспользует: синтаксис-адаптацию, DEDUP (дубли существующих квест-NPC), BOUNDARY (карты
  вне map_index), UNRESOLVED (renewal-feature/broken-синтаксис блоки), ORPHAN, defensive
  item-filter (quest-награды).
- **token-gap (26, покрыт паттерном)**: CLASS E (isbegin_quest/getnpcid/vip_status/
  getargcount→const), UNRESOLVED-comment (clear/sit/stand/delequip/mesitemlink/questinfo/
  cloakonnpc/charat/substr/floor/round/replacestr/npcskill/setpcblock/showscript/close3/
  freeloop/getfreecell/kick). Часть renewal-feature-квестов выпадет (faithful).

## Подход (общий)

Генератор СОБИРАЕТСЯ из `backport-renewal-town-npcs.py` (adapt_text) + reusable-функции
`backport-renewal-merchants.py` (block_filter/existing_npc_index/defined_in/orphan/
convert_shop_line) + quest-специфичный tail (file-list + gen/verify) — точно как
`backport-renewal-smallnpc.py` (SP-3): slice `def ua_item_ids`..`def gen(` AFTER ua_item_ids,
inject `import subprocess`, defined_in module-level, один main-guard.

## Изоляция и верификация

- `db/quest_db.txt` append (1073); `npc/backport/re_quests/*.txt`; include-блок в
  `npc/scripts_athena.conf` + scope-карты в `conf/maps_athena.conf` (append-only).
- Вывод latin-1 (8-бит диалоги); UTF-8 для Doc/-логов.
- Конвертер + генератор `--selftest`/`--verify`; boot-parse `--run_once` (0 script-error на
  `backport/re_quests`, 0 quest_db-load errors, Server ready). gap-логи в `Doc/`.

## Фазы (коммиты)

- **2-pre**: quest_db конвертер + quest_db.txt; boot quest_db-load verify.
- **2a**: quest-NPC генератор + re_quests/ + wiring + gap-лог + changes; boot-parse.

За тестерами: достижимость квестов, диалоги/цепочки, баланс наград, `.gat` зон (уже отмечено
прошлыми фазами). dropped renewal-feature квесты — для будущего движкового порта.

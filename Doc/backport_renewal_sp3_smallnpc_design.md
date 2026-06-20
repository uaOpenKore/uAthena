# SP-3 Design: мелкие renewal-NPC (guides + other + taekwon)

Статус: ДИЗАЙН СОГЛАСОВАН (brainstorming). Под-проект 3 роадмапа
`Doc/backport_renewal_content_roadmap.md` (порядок 1→3→2). Ветка x64. 0 правок движка.
Источник: rAthena `7f08087`. Переиспользует активы SP-1 ([[backport-renewal-content-series]]).

## Цель

Бэкпортировать мелкие renewal-NPC: навигаторы новых зон, разные служебные/флейвор-NPC,
expanded-класс taekwon. Малый под-проект (~5.5K строк IN), переиспользует расширенный
`adapt_text` (12+ синтаксис-классов) + `block_filter` (DEDUP/BOUNDARY/UNRESOLVED/ORPHAN)
из SP-1.

## Scope (вход)

- **guides** (7 новых зон, ~736 строк): dewata, dicastes, eclage, malangdo, malaya, mora,
  rockridge. Остальные 25 guides — дубли существующих uAthena-городов → block_filter DEDUP.
- **other** (12 IN, ~4.7K): TrainingZone123, adven_boards (3.3K), dimensional_gap (568),
  item_merge, kachua_key, mail, pvp, resetskill, stone_change, turbo_track, bulletin_boards,
  global_npcs.
- **taekwon** (jobs/taekwon.txt, 9 строк) — expanded 2nd-class (uAthena имеет TaeKwon).

## НЕ в scope (OUT)

- `other/achievements.txt` — uAthena своя реализация (done, overlap).
- `other/clans.txt` — нет clan-движка (`clan.c` absent).
- `other/CashShop_Functions.txt` — нет cash-shop.
- `other/mercenary_rent.txt` — mercenary done (свой).
- `guides/guides_woe_te.txt` — WoE:TE (нет движка).

## Подход

Генератор `dumps/forge/backport-renewal-smallnpc.py` — собран как SP-1 merchant
(town-функции из `backport-renewal-town-npcs.py` + специфика), переиспользует:
- `adapt_text`: `=`→set / `+=` / `++`/`--` / inline-if / callshop / movenpc / gap-в-условии
  (CLASS E: getnpcid/guild_has_permission/getargcount→const/comment) / consumeitem→delitem /
  byte-preserving latin-1.
- `block_filter` + global orphan-pass: DEDUP (дубли guides существующих городов),
  BOUNDARY (NPC на картах вне map_index), UNRESOLVED (live-gap/broken-синтаксис), ORPHAN
  (осиротевшие duplicate).

Вывод → `npc/backport/re_other/` (единое дерево для guides+other+taekwon).

## gap-решения

- Покрыто adapt_text: `consumeitem`→delitem, `getnpcid`/`guild_has_permission`/`getargcount`
  → CLASS E/COMMENT/block.
- Нет аналога (`charat`/`mergeitem`/`mesitemlink`/`mail`) → block_filter UNRESOLVED-comment
  (faithful; частично затронуты TrainingZone/adven_boards/item_merge/kachua_key/mail).
- **dimensional_gap**: NPC на карте `dali` (вне map_index) → BOUNDARY-comment (как
  warps-фаза; `dali`-хаб = отдельная будущая единица). Завершает оставленный boundary из
  [[backport-renewal-warps-npc]].

## Изоляция и верификация

- `npc/backport/re_other/*.txt`; include-блок в `npc/scripts_athena.conf` (append-only);
  scope-карты в `conf/maps_athena.conf` (collect-used).
- Вывод latin-1 (8-битные диалоги), UTF-8 для Doc/-логов.
- `--selftest`/`--verify` (имена/тайлы/refs/live-gap/unreg/braces) + boot-parse `--run_once`
  (0 script-error на `backport/re_other`, Server ready).
- gap-лог `Doc/backport_renewal_smallnpc_gap.md`.

## Фаза (один коммит)

R3: генератор + re_other/ + wiring + gap-лог + changes. (Меньше SP-1 — guides+other+taekwon
не имеют item-добора; предметы guides/other продают — проверить item-gap, дефолт defensive
item-filter уже в генераторе-паттерне.)

За тестерами: `.gat` renewal-карт guides (новые зоны) + dali (dimensional_gap), достижимость,
диалоги.

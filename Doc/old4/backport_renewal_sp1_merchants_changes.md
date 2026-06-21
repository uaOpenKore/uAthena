# SP-1 Renewal merchants + item-backport — изменения

Источник: rAthena `7f08087`. Ветка x64. 0 правок движка. Под-проект 1 роадмапа
`Doc/backport_renewal_content_roadmap.md`. Дизайн/план: `..._sp1_merchants_{design,plan}.md`.

## R1a — item-добор (93 предмета) · commit accbbc1

`db/item_db2.txt`: 1335 → 1428 (+93 renewal-предмета, продаваемых IN-магазинами).
Конвертер `dumps/forge/backport-renewal-shop-items.py` (yml→TXT, база cards). Скрипты:
**43 keep / 15 drop→`{}` / 35 без скрипта**. eLV>99→99, job=all. Dropped-оригиналы —
`Doc/backport_renewal_shop_item_scripts.txt`. Boot item-load: 0 errors.

## R1b — магазины (55 файлов)

Генератор `dumps/forge/backport-renewal-merchants.py` (на базе renewal-town-npcs +
merchant-специфика). Вывод `npc/backport/re_merchants/` + `_renewal_functions.txt`
(F_getpositionname/F_IsCharm портированы из rAthena Global_Functions). Подключение:
`npc/scripts_athena.conf` (56 includes) + `conf/maps_athena.conf` (+8 карт).

**Адаптация (события):** ADAPT 1176 (=→set, ++/--, compound, callshop, movenpc, inline-if,
gap-в-условии→const), MARKETSHOP→shop 44, SITEFIX 1.

**Что НЕ добавлено (faithful — документировано в gap-логе):**
- **DEDUP 64** — магазины, дублирующие существующие uAthena NPC (refine/shops/refiners):
  имя/тайл уже есть → skip (как warp merge-rule).
- **UNRESOLVED 102** — NPC на renewal-фичах (refineui/stylist/setunittitle/delequip/
  mesitemlink/getequiprefinecost/sprintf) или broken-синтаксис (тернарник+func, многострочный
  select, ++index, source-typo) → block-comment (не работают в pre-renewal движке).
- **ORPHAN 212** — `duplicate()` чья база закомментирована/отсутствует → comment.
- **BOUNDARY 151** — NPC на картах вне map_index (lhz_dun_n/paramk/rgsr_in/job3_* и т.д.).

**Что работает:** ~106 живых merchant-NPC (новые renewal-магазины: enchanters, costume,
exchanges, classic-refiners, traders).

## Адаптация синтаксиса (общий adapt_text, +town-NPC выигрывает)

Расширен `adapt_text` (town-npcs.py, shared): CLASS A (`=`→set, +trailing-comment, +bare/
`$`-vars), CLASS A-compound (`+=`/`-=`→set), CLASS D (for-init/`++`/`--`, prefix+postfix,
index-guard), CLASS E (gap-в-условии inarray/isbegin_quest/jobcanentermap/checkmadogear/
getequiparmorlv→const), callshop+flag, movenpc-dropdir, block_filter (DEDUP/BOUNDARY/
UNRESOLVED/BROKEN) + global orphan-pass. Town-NPC регенерирован (1 строка eclage: `set Zeny`).

## Верификация

- Конвертер + генератор `--selftest` зелёные; merchant `--verify` **OK** (0 gap/collisions/
  refs/unreg/brace; shop-items resolved).
- Финальный boot `--run_once`: **0 script errors** (вся загрузка), item_db2=1428, Server ready.

## За тестерами (нужен клиент + GRF)

- `.gat` в GRF: renewal-карты магазинов + `itemmall` (1 boot bad-duplicate — base Equipment
  Reform на itemmall, на dev-боксе карта removed без .gat; на проде с .gat резолвится).
- Достижимость (boundary-карты = renewal-данжи, отдельные будущие единицы), баланс цен,
  диалоги. SQL item_db регенерация если `use_sql_db`.
- 15 dropped item-scripts + UNRESOLVED renewal-NPC — для будущего движкового порта.

# SP-1 Design: бэкпорт renewal-магазинов + item-добор (rAthena → uAthena)

Статус: ДИЗАЙН СОГЛАСОВАН (brainstorming). Под-проект 1 из роадмапа
[[backport-renewal-content-roadmap]] (`Doc/backport_renewal_content_roadmap.md`).
Ветка x64. 0 правок движка. Источник: rAthena `7f08087`, `/tmp/rathena-ref`.

## Цель

Бэкпортировать renewal-магазины (`npc/re/merchants/`, 55 IN файлов ~23.8K строк) в
uAthena, адаптируя синтаксис под старый движок. Магазины продают renewal-предметы →
**сначала добор 93 отсутствующих предмета** в item_db, потом сами магазины.

Две части (порядок 1a → 1b): **1a item-добор** (93 предмета), **1b магазины** (NPC).

## SP-1a — item-добор (93 предмета)

- **Цель**: `db/item_db2.txt` (append; сейчас 1335 = lv4 894 + cards 441 → ~1428).
  22-полевой TXT: `ID,AegisName,Name,Type,Buy,Sell,Weight,ATK,DEF,Range,Slots,Job,Upper,
  Gender,Loc,wLV,eLV,Refineable,View,{Script},{OnEquip},{OnUnequip}`.
- **Источник**: rAthena `db/re/item_db_{usable,equip,etc}.yml` (все 93 найдены: usable 25,
  equip 13, etc 55). Типы: Etc 33, Ammo 22, Weapon 10, Healing 9, Usable 9, DelayConsume 7,
  Armor 3.
- **Конвертер** `dumps/forge/backport-renewal-shop-items.py` (база — `backport-renewal-cards.py`
  + `backport-lv4-items.py`): yml→TXT. Type-маппинг (Healing→0, Usable→2, Etc→3, Weapon→4,
  Armor→5, Ammo→10, DelayConsume→11). Для equip (13): eLV>99→99, 3rd-4th job→2nd (lv4-правило).
- **Санитайзер скриптов** `script_is_safe` (прецедент cards): токен валиден ⇔ const ∪ buildin ∪
  skill ∪ keyword; `.@`/unknown → скрипт дропается в `{}`. Оценка: **43 keep, 15 drop→`{}`,
  35 без скрипта**. Dropped-оригиналы → `Doc/backport_renewal_shop_item_scripts.txt`.
- **ID-конфликтов нет** (93 строго missing). SQL (`A-item_db.sql`) не трогаем — рантайм читает
  TXT (`use_sql_db: no`); регенерация SQL = deploy-задача, отмечается в changes.

## SP-1b — магазины (55 файлов)

- **Вход**: `npc/re/merchants/*.txt` минус 4 OUT (cashmall, cash_trader, enchan_illusion_17_1,
  mysterious_cookie_shop) и `barters/` (`.yml`). → `npc/backport/re_merchants/`.
- **Типы сущностей**: shop 135 / script 306 / duplicate 611 — портируемы. `marketshop` 44 →
  `shop` (убрать `:stock`-поле, `price=-1`→item_db buy). `cashshop` — N/A (все в OUT-файлах).
- **Placement**: 388 placed + 99 floating (floating = `-`/FAKE/HIDDEN marketshop через callshop,
  грузятся независимо от карт).
- **Генератор** `dumps/forge/backport-renewal-merchants.py` на базе
  `backport-renewal-town-npcs.py`: переиспользует `adapt_text` (синтаксис-классы `=→set`,
  `++`/`--`, `enablenpc()`, string-literal guard, byte-preserving latin-1), token-gap-санитайзер,
  BOUNDARY, `collect_used_scope_maps`. Добавляет: shop-семейство + `marketshop`→`shop` конверсия.
- **defensive item-фильтр**: после 1a item-gap=0; на случай недобора генератор убирает
  отсутствующие item-id из shop-списков + лог (иначе фантом+warning, см. `itemdb_search` dummy).

## Адаптация (наследуется + специфика)

- **Синтаксис-классы** (из [[backport-renewal-warps-npc]]): `=→set`, for-init/`++`/`--`,
  `enablenpc()→strnpcinfo(0)`, string-literal guard, SITEFIX, byte-preserve. Token-gap по
  buildins (`gap = rAthena − uAthena`).
- **marketshop→shop**: `SPRITE,id:price:stock,...` → `SPRITE,id:price,...` (drop 3-е под-поле).
- **BOUNDARY**: placed-NPC на незарегистрированных renewal-картах (`lhz_dun_n` Nightmare Biolab,
  `paramk`, `rgsr_in`, `har_in01`) → comment+log (недостижимы; отдельные будущие единицы).
  Floating (callshop) — keep.
- **callshop/callfunc-зависимости**: проверить, что floating marketshop, вызываемые из
  placed-NPC, не осиротели после boundary-skip (gap-лог).

## Изоляция и подключение (append-only)

- item_db2.txt — append 93 предмета.
- `npc/backport/re_merchants/*.txt` — вывод магазинов; include-блок в `npc/scripts_athena.conf`
  (`// ===== Backport renewal merchants (GENERATED) =====`).
- `conf/maps_athena.conf` — merchant-карты ∈ map_index (collect_used_scope_maps).
- Вывод латин-1 для NPC (8-битные диалоги), UTF-8 для doc-логов.

## Верификация (без клиента)

1. Конвертер `--selftest` (санитайзер-фикстуры) + item_db2 boot-load: **0 item-parse errors**
   (нет «does not exist»/«Using dummy» на доборенных id).
2. Магазины `--selftest`/`--verify` (имена/braces/refs/live-gap/unregistered-maps).
3. **boot-parse `--run_once`** (MariaDB up): 0 script-error на `backport/re_merchants`,
   0 shop-item warning, `Server is 'ready'`.
4. gap-логи: dropped item-scripts, boundary-NPC, адаптированные команды.

За тестерами: достижимость магазинов (boundary-карты нужны портирование локаций), баланс цен,
`.gat` renewal-карт магазинов в GRF; SQL-регенерация item_db если используется.

## Фазы (коммиты)

- **R1a** item-добор: конвертер + item_db2.txt + dropped-script лог; boot item-load verify.
- **R1b** магазины: генератор + re_merchants/ + maps_conf + scripts_athena.conf; boot-parse verify.

## НЕ в scope (OUT)

barter (16 yml), cash-shop (cashmall/cash_trader), 3rd-job merchants (enchan_illusion_17_1,
mysterious_cookie_shop), магазины на непортированных renewal-локациях (boundary-skip), SQL-добор
(deploy). Renewal-механики market/cash → деградируют в обычный zeny-shop.
